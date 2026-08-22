import frappe
import requests


@frappe.whitelist()
def sync_dcu_status():
    settings = frappe.get_single("URL Setup Settings")
    url = f"{settings.base_url}/api/concentratorOnlineStatus/read"
    body = {
        "lang": "en",
        "pageNumber": 1,
        "pageSize": 20,
        "concentratorId": None,
        "status": None,
        "remark": None,
        "orderBy": "concentratorId asc",
        "searchTerm": None,
        "Company": settings.company
    }
    headers = {"Authorization": f"Bearer {settings.get_password('api_token')}"}

    response = requests.post(url, json=body, headers=headers, timeout=30)
    payload = response.json()

    if payload.get("code") != 0:
        frappe.log_error(payload, "DCU Status Sync Failed")
        return

    for row in payload["result"]["data"]:
        dcu = frappe.db.exists("DCU", row["concentratorId"])
        if not dcu:
            frappe.log_error(f"Unmapped DCU ID: {row['concentratorId']}", "Calin Unmapped DCU")
            continue

        frappe.db.set_value("DCU", dcu, {
            "status": "Online" if row["status"] else "Offline",
            "last_seen": frappe.utils.get_datetime(row["statusUpdateDate"])
        })

    frappe.db.commit()


def sync_water_meter(meter_id):
    settings = frappe.get_single("URL Setup Settings")
    url = f"{settings.base_url}/api/account/read"
    body = {
        "pageNumber": 1,
        "pageSize": 1,
        "customerId": None,
        "meterId": meter_id,
        "tariffId": None,
        "remark": None,
        "createDateRange": None,
        "updateDateRange": None,
        "orderBy": "customerId asc",
        "searchTerm": None,
        "Company": settings.company
    }
    headers = {"Authorization": f"Bearer {settings.get_password('api_token')}"}

    response = requests.post(url, json=body, headers=headers, timeout=30)
    payload = response.json()

    if payload.get("code") != 0:
        frappe.log_error(payload, f"Water Meter Sync Failed: {meter_id}")
        return

    data = payload["result"]["data"]
    if not data:
        frappe.log_error(f"No Calin account found for meter: {meter_id}", "Unmapped Meter")
        return

    row = data[0]

    if not frappe.db.exists("Water Meter", meter_id):
        frappe.log_error(f"Water Meter {meter_id} not found locally", "Unmapped Meter")
        return

    doc = frappe.get_doc("Water Meter", meter_id)

    doc.calin_customer_id = row.get("customerId")
    doc.tariff_id = row.get("tariffId")
    doc.meter_type = row.get("meterType")
    doc.protocol_version = row.get("protocolVersion")
    doc.datetime_zrga = frappe.utils.now_datetime()

    concentrator_id = row.get("concentratorId")
    if concentrator_id and frappe.db.exists("DCU", concentrator_id):
        doc.dcu = concentrator_id
    elif concentrator_id:
        frappe.log_error(f"Unmapped DCU ID: {concentrator_id}", "Calin Unmapped DCU")

    doc.save()
    frappe.db.commit()


def sync_all_water_meters():
    meters = frappe.db.get_all("Water Meter", pluck="meter_id")
    for meter_id in meters:
        try:
            sync_water_meter(meter_id)
        except Exception:
            frappe.log_error(frappe.get_traceback(), f"Water Meter Sync Error: {meter_id}")


def sync_meter_readings(meter_id):
    settings = frappe.get_single("URL Setup Settings")
    url = f"{settings.base_url}/api/dailydatawater/read"
    headers = {"Authorization": f"Bearer {settings.get_password('api_token')}"}
    body = {
        "lang": "en",
        "pageNumber": 1,
        "pageSize": 20,
        "meterId": meter_id,
        "remark": None,
        "createDateRange": None,
        "updateDateRange": None,
        "orderBy": None,
        "searchTerm": None,
        "Company": settings.company
    }

    response = requests.post(url, json=body, headers=headers, timeout=30)
    payload = response.json()

    if payload.get("code") != 0:
        frappe.log_error(payload, f"Meter Reading Sync Failed: {meter_id}")
        return

    if not frappe.db.exists("Water Meter", meter_id):
        frappe.log_error(f"Water Meter {meter_id} not found locally", "Unmapped Meter Reading")
        return

    for row in payload["result"]["data"]:
        reading_date = frappe.utils.get_datetime(row["currentDate"])

        existing = frappe.db.exists("Meter Reading", {
            "meter": meter_id,
            "reading_date": reading_date
        })
        if existing:
            continue

        doc = frappe.get_doc({
            "doctype": "Meter Reading",
            "meter": meter_id,
            "reading_date": reading_date,
            "cumulative_reading": row.get("total"),
            "recharge_balance": row.get("currentRechargeBalance"),
            "concentrator_id": row.get("concentratorId"),
            "valve_status": 1 if row.get("valveStatus") else 0,
            "magnetic_interference": 1 if row.get("magneticInterference") else 0,
            "battery_status": 1 if row.get("batteryStatus") else 0,
        })
        doc.insert()

    frappe.db.commit()


@frappe.whitelist()
def sync_all_meter_readings():
    settings = frappe.get_single("URL Setup Settings")
    headers = {"Authorization": f"Bearer {settings.get_password('api_token')}"}

    url = f"{settings.base_url}/api/dailydatawater/read"
    body = {
        "lang": "en", "pageNumber": 1, "pageSize": 500, "meterId": None,
        "remark": None, "createDateRange": None, "updateDateRange": None,
        "orderBy": None, "searchTerm": None, "Company": settings.company
    }
    response = requests.post(url, json=body, headers=headers, timeout=30)
    payload = response.json()

    if payload.get("code") != 0:
        frappe.log_error(payload, "Meter Reading Sync Failed")
        frappe.msgprint(f"Sync failed: {payload.get('reason')}")
        return

    created, updated, skipped = 0, 0, 0

    for row in payload["result"]["data"]:
        meter_id = row.get("meterId")
        if not meter_id:
            skipped += 1
            continue

        if not frappe.db.exists("Water Meter", meter_id):
            skipped += 1
            continue

        reading_date = frappe.utils.get_datetime(row["currentDate"]) if row.get("currentDate") else None
        updated_date = frappe.utils.get_datetime(row["updateDate"]) if row.get("updateDate") else None

        fields = {
            "customer_name": row.get("customerName"),
            "cumulative_reading": row.get("total"),
            "recharge_balance": row.get("currentRechargeBalance"),
            "total_recharge_balance": row.get("totalRechargeBalance"),
            "concentrator_id": row.get("concentratorId"),
            "remark": row.get("remark"),
            "valve_status": 1 if row.get("valveStatus") else 0,
            "magnetic_interference": 1 if row.get("magneticInterference") else 0,
            "battery_status": 1 if row.get("batteryStatus") else 0,
            "updated_date": updated_date
        }

        existing = frappe.db.exists("Meter Reading", {"meter": meter_id, "reading_date": reading_date})

        if not existing:
            fields["doctype"] = "Meter Reading"
            fields["meter"] = meter_id
            fields["reading_date"] = reading_date
            doc = frappe.get_doc(fields)
            doc.insert(ignore_permissions=True)
            created += 1
        else:
            frappe.db.set_value("Meter Reading", existing, fields)
            updated += 1

    frappe.db.commit()
    frappe.msgprint(f"Meter Reading sync complete: {created} created, {updated} updated, {skipped} skipped")
@frappe.whitelist()
def sync_all_token_records():
    settings = frappe.get_single("URL Setup Settings")
    headers = {"Authorization": f"Bearer {settings.get_password('api_token')}"}

    url = f"{settings.base_url}/api/token/creditWaterTokenRecord/read"
    body = {
        "pageNumber": 1, "pageSize": 500, "receiptId": None, "status": True,
        "customerId": None, "customerName": None, "meterId": None, "meterType": None,
        "tariffId": None, "remark": None, "token": None, "createDateRange": None,
        "updateDateRange": None, "orderBy": "receiptId desc", "searchTerm": None,
        "Company": settings.company
    }
    response = requests.post(url, json=body, headers=headers, timeout=30)
    payload = response.json()

    if payload.get("code") != 0:
        frappe.log_error(payload, "Token Record Sync Failed")
        frappe.msgprint(f"Sync failed: {payload.get('reason')}")
        return

    created, updated, skipped = 0, 0, 0

    for row in payload["result"]["data"]:
        receipt_id = str(row.get("receiptId"))
        meter_id = row.get("meterId")

        if not receipt_id or not meter_id:
            skipped += 1
            continue

        if not frappe.db.exists("Water Meter", meter_id):
            skipped += 1
            continue

        created_date = frappe.utils.get_datetime(row["createDate"]) if row.get("createDate") else None
        update_date = frappe.utils.get_datetime(row["updateDate"]) if row.get("updateDate") else None

        fields = {
            "customer_id": row.get("customerId"),
            "customer_name": row.get("customerName"),
            "tariff_id": row.get("tariffId"),
            "amount_paid": row.get("totalPaid"),
            "token": row.get("token"),
            "token_first": row.get("tokenFirst"),
            "token_second": row.get("tokenSecond"),
            "total_unit": row.get("totalUnit"),
            "repayment_amount": row.get("repaymentAmount"),
            "debt_remaining": row.get("debtRemaining"),
            "closing_balance": row.get("closingBalance"),
            "remark": row.get("remark"),
            "created_date": created_date,
            "updated_dat": update_date
        }

        if not frappe.db.exists("Token Record", receipt_id):
            fields["doctype"] = "Token Record"
            fields["receipt_id"] = receipt_id
            fields["meter"] = meter_id
            doc = frappe.get_doc(fields)
            doc.insert(ignore_permissions=True)
            created += 1
        else:
            frappe.db.set_value("Token Record", receipt_id, fields)
            updated += 1

    frappe.db.commit()
    frappe.msgprint(f"Token Record sync complete: {created} created, {updated} updated, {skipped} skipped")
def sync_all_dcus():
    settings = frappe.get_single("URL Setup Settings")
    headers = {"Authorization": f"Bearer {settings.get_password('api_token')}"}

    loc_url = f"{settings.base_url}/api/concentrator/read"
    loc_body = {
        "pageNumber": 1, "pageSize": 500, "concentratorId": None, "name": None,
        "lat": None, "lng": None, "remark": None, "createDateRange": None,
        "updateDateRange": None, "orderBy": "concentratorId asc", "searchTerm": None,
        "Company": settings.company
    }
    loc_response = requests.post(loc_url, json=loc_body, headers=headers, timeout=30)
    loc_payload = loc_response.json()

    if loc_payload.get("code") != 0:
        frappe.log_error(loc_payload, "DCU Location Fetch Failed")
        return

    locations = {}
    for row in loc_payload["result"]["data"]:
        locations[row["concentratorId"]] = {
            "dcu_name": row.get("name"),
            "latitude": row.get("lat"),
            "longitude": row.get("lng")
        }

    status_url = f"{settings.base_url}/api/concentratorOnlineStatus/read"
    status_body = {
        "lang": "en", "pageNumber": 1, "pageSize": 500, "concentratorId": None,
        "status": None, "remark": None, "orderBy": "concentratorId asc",
        "searchTerm": None, "Company": settings.company
    }
    status_response = requests.post(status_url, json=status_body, headers=headers, timeout=30)
    status_payload = status_response.json()

    if status_payload.get("code") != 0:
        frappe.log_error(status_payload, "DCU Status Fetch Failed")
        return

    statuses = {}
    for row in status_payload["result"]["data"]:
        statuses[row["concentratorId"]] = {
            "status": "Online" if row.get("status") else "Offline",
            "last_seen": frappe.utils.get_datetime(row["statusUpdateDate"]) if row.get("statusUpdateDate") else None
        }

    all_ids = set(locations.keys()) | set(statuses.keys())
    created, updated = 0, 0

    for dcu_id in all_ids:
        loc = locations.get(dcu_id, {})
        stat = statuses.get(dcu_id, {})
        has_location = loc.get("latitude") and loc.get("longitude")
        exists = frappe.db.exists("DCU", dcu_id)

        if not exists:
            doc = frappe.get_doc({
                "doctype": "DCU",
                "dcu_id": dcu_id,
                "dcu_name": loc.get("dcu_name") or dcu_id,
                "latitude": loc.get("latitude"),
                "longitude": loc.get("longitude"),
                "status": stat.get("status") or "Offline",
                "last_seen": stat.get("last_seen")
            })
            doc.insert(ignore_permissions=True)
            created += 1
        else:
            if has_location:
                doc = frappe.get_doc("DCU", dcu_id)
                doc.dcu_name = loc.get("dcu_name") or doc.dcu_name
                doc.latitude = loc.get("latitude")
                doc.longitude = loc.get("longitude")
                if stat:
                    doc.status = stat.get("status")
                    doc.last_seen = stat.get("last_seen")
                doc.save(ignore_permissions=True)
            elif stat:
                frappe.db.set_value("DCU", dcu_id, {
                    "status": stat.get("status"),
                    "last_seen": stat.get("last_seen")
                })
            updated += 1

    frappe.db.commit()
    frappe.msgprint(f"DCU sync complete: {created} created, {updated} updated")


@frappe.whitelist()
def sync_all_water_meters():
    settings = frappe.get_single("URL Setup Settings")
    headers = {"Authorization": f"Bearer {settings.get_password('api_token')}"}

    url = f"{settings.base_url}/api/account/read"
    body = {
        "pageNumber": 1, "pageSize": 500, "customerId": None, "meterId": None,
        "tariffId": None, "remark": None, "createDateRange": None,
        "updateDateRange": None, "orderBy": "customerId asc", "searchTerm": None,
        "Company": settings.company
    }
    response = requests.post(url, json=body, headers=headers, timeout=30)
    payload = response.json()

    if payload.get("code") != 0:
        frappe.log_error(payload, "Water Meter Sync Failed")
        frappe.msgprint(f"Sync failed: {payload.get('reason')}")
        return

    created, updated = 0, 0

    for row in payload["result"]["data"]:
        meter_id = row.get("meterId")
        if not meter_id:
            continue

        concentrator_id = row.get("concentratorId")
        dcu_link = concentrator_id if concentrator_id and frappe.db.exists("DCU", concentrator_id) else None

        updated_date = frappe.utils.get_datetime(row["updateDate"]) if row.get("updateDate") else None
        created_date = frappe.utils.get_datetime(row["createDate"]) if row.get("createDate") else None

        fields = {
            "calin_customer_id": row.get("customerId"),
            "customer_name": row.get("customerName"),
            "tariff_id": row.get("tariffId"),
            "meter_type": row.get("meterType"),
            "protocol_version": row.get("protocolVersion"),
            "site": row.get("site"),
            "remark": row.get("remark"),
            "updated_date": updated_date,
            "created_date": created_date,
            "dcu": dcu_link
        }

        if not frappe.db.exists("Water Meter", meter_id):
            fields["doctype"] = "Water Meter"
            fields["meter_id"] = meter_id
            doc = frappe.get_doc(fields)
            doc.insert(ignore_permissions=True)
            created += 1
        else:
            frappe.db.set_value("Water Meter", meter_id, fields)
            updated += 1

    frappe.db.commit()
    frappe.msgprint(f"Water Meter sync complete: {created} created, {updated} updated")

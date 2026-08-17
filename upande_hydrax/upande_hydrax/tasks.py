import frappe
import requests


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


def sync_all_meter_readings():
    meters = frappe.db.get_all("Water Meter", pluck="meter_id")
    for meter_id in meters:
        try:
            sync_meter_readings(meter_id)
        except Exception:
            frappe.log_error(frappe.get_traceback(), f"Meter Reading Sync Error: {meter_id}")


def sync_token_records(meter_id):
    settings = frappe.get_single("URL Setup Settings")
    url = f"{settings.base_url}/api/token/creditWaterTokenRecord/read"
    headers = {"Authorization": f"Bearer {settings.get_password('api_token')}"}
    body = {
        "pageNumber": 1,
        "pageSize": 20,
        "receiptId": None,
        "status": True,
        "customerId": None,
        "customerName": None,
        "meterId": meter_id,
        "meterType": None,
        "tariffId": None,
        "remark": None,
        "token": None,
        "createDateRange": None,
        "updateDateRange": None,
        "orderBy": "receiptId desc",
        "searchTerm": None,
        "Company": settings.company
    }

    response = requests.post(url, json=body, headers=headers, timeout=30)
    payload = response.json()

    if payload.get("code") != 0:
        frappe.log_error(payload, f"Token Record Sync Failed: {meter_id}")
        return

    for row in payload["result"]["data"]:
        receipt_id = str(row.get("receiptId"))

        if frappe.db.exists("Token Record", receipt_id):
            doc = frappe.get_doc("Token Record", receipt_id)
        else:
            doc = frappe.get_doc({
                "doctype": "Token Record",
                "receipt_id": receipt_id,
                "meter": meter_id
            })

        doc.amount_paid = row.get("totalPaid")
        doc.token = row.get("token")
        doc.token_first = row.get("tokenFirst")
        doc.token_second = row.get("tokenSecond")
        doc.total_unit = row.get("totalUnit")
        doc.repayment_amount = row.get("repaymentAmount")
        doc.debt_remaining = row.get("debtRemaining")
        doc.closing_balance = row.get("closingBalance")

        if doc.is_new():
            doc.insert()
        else:
            doc.save()

    frappe.db.commit()


def sync_all_token_records():
    meters = frappe.db.get_all("Water Meter", pluck="meter_id")
    for meter_id in meters:
        try:
            sync_token_records(meter_id)
        except Exception:
            frappe.log_error(frappe.get_traceback(), f"Token Record Sync Error: {meter_id}")

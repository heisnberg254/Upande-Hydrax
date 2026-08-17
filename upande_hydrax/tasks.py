import frappe
import requests

def sync_dcu_status():
    settings = frappe.get_single("URL Setup Settings")
    url = f"{settings.base_url}/api/concentrator/concentrator-online-status/read"
    body = {"concentratorId": None, "Company": settings.company}
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
            "last_seen": row["statusUpdateDate"]
        })
    frappe.db.commit()

def sync_calin_daily_data():
    settings = frappe.get_single("URL Setup Settings")
    headers = {"Authorization": f"Bearer {settings.get_password('api_token')}"}

    page = 1
    while True:
        url = f"{settings.base_url}/api/dailydatawater/read"
        body = {
            "lang": "en",
            "pageNumber": page,
            "pageSize": 100,
            "meterId": None,
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
            frappe.log_error(payload, "Calin Daily Data Sync Failed")
            return

        rows = payload["result"]["data"]
        if not rows:
            break

        for row in rows:
            process_daily_reading(row)

        if page * 100 >= payload["result"]["total"]:
            break
        page += 1

    frappe.db.commit()


def process_daily_reading(row):
    if row["total"] == -1:
        frappe.log_error(f"Meter {row['meterId']} did not report on {row['currentDate']}", "Calin No Report")
        return

    meter = frappe.db.exists("Water Meter", row["meterId"])
    if not meter:
        frappe.log_error(f"Unmapped meter ID: {row['meterId']}", "Calin Unmapped Meter")
        return

    exists = frappe.db.exists("Meter Reading", {
        "meter": meter,
        "reading_datetime": row["currentDate"]
    })
    if exists:
        return

    frappe.get_doc({
        "doctype": "Meter Reading",
        "meter": meter,
        "concentrator_id": row["concentratorId"],
        "reading_datetime": row["currentDate"],
        "cumulative_volume": row["total"],
        "recharge_balance": row["currentRechargeBalance"],
        "valve_status": 1 if row["valveStatus"] else 0,
        "magnetic_interference": 1 if row["magneticInterference"] else 0,
        "battery_status": 1 if row["batteryStatus"] else 0
    }).insert(ignore_permissions=True)

    frappe.db.set_value("Water Meter", meter, "token_balance", row["currentRechargeBalance"])

def sync_calin_daily_data():
    settings = frappe.get_single("URL Setup Settings")
    headers = {"Authorization": f"Bearer {settings.get_password('api_token')}"}
    url = f"{settings.base_url}/api/dailydatawater/read"

    meters = frappe.get_all("Water Meter", pluck="name")

    for meter_id in meters:
        body = {
            "lang": "en",
            "pageNumber": 1,
            "pageSize": 5,  # just the most recent few days per meter, for now
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
            frappe.log_error(payload, f"Calin Daily Data Sync Failed for {meter_id}")
            continue

        for row in payload["result"]["data"]:
            process_daily_reading(row)

    frappe.db.commit()


def process_daily_reading(row):
    if row["total"] == -1:
        return  # meter didn't report that day, skip quietly

    meter = frappe.db.exists("Water Meter", row["meterId"])
    if not meter:
        frappe.log_error(f"Unmapped meter ID: {row['meterId']}", "Calin Unmapped Meter")
        return

    exists = frappe.db.exists("Meter Reading", {
        "meter": meter,
        "reading_datetime": row["currentDate"]
    })
    if exists:
        return

    frappe.get_doc({
        "doctype": "Meter Reading",
        "meter": meter,
        "concentrator_id": row["concentratorId"],
        "reading_datetime": row["currentDate"],
        "cumulative_volume": row["total"],
        "recharge_balance": row["currentRechargeBalance"],
        "valve_status": 1 if row["valveStatus"] else 0,
        "magnetic_interference": 1 if row["magneticInterference"] else 0,
        "battery_status": 1 if row["batteryStatus"] else 0
    }).insert(ignore_permissions=True)

    frappe.db.set_value("Water Meter", meter, "token_balance", row["currentRechargeBalance"])

def sync_token_records():
    settings = frappe.get_single("URL Setup Settings")
    headers = {"Authorization": f"Bearer {settings.get_password('api_token')}"}
    url = f"{settings.base_url}/api/token/creditWaterTokenRecord/read"

    meters = frappe.get_all("Water Meter", pluck="name")

    for meter_id in meters:
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
            frappe.log_error(payload, f"Token Record Sync Failed for {meter_id}")
            continue

        for row in payload["result"]["data"]:
            process_token_record(row)

    frappe.db.commit()


def process_token_record(row):
    if frappe.db.exists("Token Record", str(row["receiptId"])):
        return  # already saved, skip

    meter = frappe.db.exists("Water Meter", row["meterId"])
    if not meter:
        frappe.log_error(f"Unmapped meter ID: {row['meterId']}", "Calin Unmapped Meter")
        return

    frappe.get_doc({
        "doctype": "Token Record",
        "receipt_id": str(row["receiptId"]),
        "meter": meter,
        "amount_paid": row["totalPaid"],
        "total_unit": row["totalUnit"],
        "token": row["token"],
        "token_first": row["tokenFirst"],
        "token_second": row["tokenSecond"],
        "repayment_amount": row["repaymentAmount"],
        "debt_remaining": row["debtRemaining"],
        "closing_balance": row["closingBalance"],
        "type": "Top Up"
    }).insert(ignore_permissions=True)

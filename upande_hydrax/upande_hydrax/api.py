import frappe


@frappe.whitelist()
def get_dashboard_summary():
    total_dcu = frappe.db.count("DCU")
    online_dcu = frappe.db.count("DCU", {"status": "Online"})
    total_meters = frappe.db.count("Water Meter")

    today = frappe.utils.nowdate()
    yesterday = frappe.utils.add_days(today, -1)
    active_meters = frappe.db.sql("""
        SELECT COUNT(DISTINCT meter) FROM `tabMeter Reading`
        WHERE DATE(reading_date) >= %s
    """, (yesterday,))[0][0] or 0

    total_consumption_today = frappe.db.sql("""
        SELECT SUM(curr.cumulative_reading - prev.cumulative_reading)
        FROM `tabMeter Reading` curr
        LEFT JOIN `tabMeter Reading` prev
            ON prev.meter = curr.meter
            AND prev.reading_date = (
                SELECT MAX(r2.reading_date)
                FROM `tabMeter Reading` r2
                WHERE r2.meter = curr.meter
                AND r2.reading_date < curr.reading_date
            )
        WHERE DATE(curr.reading_date) = %s
            AND curr.cumulative_reading IS NOT NULL AND curr.cumulative_reading != -1
            AND prev.cumulative_reading IS NOT NULL AND prev.cumulative_reading != -1
    """, (today,))[0][0] or 0

    return {
        "total_dcu": total_dcu,
        "online_dcu": online_dcu,
        "total_meters": total_meters,
        "active_meters": active_meters,
        "total_consumption_today": round(total_consumption_today, 1)
    }


@frappe.whitelist()
def get_map_points(site: str = None):
    dcus_raw = frappe.db.get_all(
        "DCU",
        fields=["dcu_id", "dcu_name", "latitude", "longitude", "status", "last_seen"],
        filters={"latitude": ["is", "set"], "longitude": ["is", "set"]}
    )
    dcus = [
        d for d in dcus_raw
        if str(d.get("latitude")).replace("\u00b0", "").strip() not in ("0", "0.0", "")
        and str(d.get("longitude")).replace("\u00b0", "").strip() not in ("0", "0.0", "")
    ]

    meter_filters = {"latitude": ["is", "set"], "longitude": ["is", "set"]}
    if site:
        meter_filters["site"] = site

    meters_raw = frappe.db.get_all(
        "Water Meter",
        fields=["meter_id", "latitude", "longitude", "house_number", "site"],
        filters=meter_filters
    )
    meters = [
        m for m in meters_raw
        if m.get("latitude") not in (0, 0.0)
        and m.get("longitude") not in (0, 0.0)
    ]

    return {"dcus": dcus, "meters": meters}


@frappe.whitelist()
def get_site_list():
    return frappe.db.get_all("Site", fields=["name"], order_by="name asc")


@frappe.whitelist()
def get_consumption_by_meter():
    today = frappe.utils.nowdate()
    data = frappe.db.sql("""
        SELECT
            curr.meter,
            curr.cumulative_reading - prev.cumulative_reading AS consumption
        FROM `tabMeter Reading` curr
        LEFT JOIN `tabMeter Reading` prev
            ON prev.meter = curr.meter
            AND prev.reading_date = (
                SELECT MAX(r2.reading_date)
                FROM `tabMeter Reading` r2
                WHERE r2.meter = curr.meter
                AND r2.reading_date < curr.reading_date
            )
        WHERE DATE(curr.reading_date) = %s
            AND curr.cumulative_reading IS NOT NULL AND curr.cumulative_reading != -1
            AND prev.cumulative_reading IS NOT NULL AND prev.cumulative_reading != -1
    """, (today,), as_dict=True)

    return {
        "labels": [row["meter"] for row in data],
        "values": [row["consumption"] or 0 for row in data]
    }

# Copyright (c) 2026, edwin@upande.com and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class MeterReading(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		battery_status: DF.Check
		concentrator_id: DF.Data | None
		cumulative_reading: DF.Float
		magnetic_interference: DF.Check
		meter: DF.Link | None
		name: DF.Int | None
		reading_date: DF.Datetime | None
		recharge_balance: DF.Float
		valve_status: DF.Check
	# end: auto-generated types

	_DOCTYPE_NAME = "Meter Reading"

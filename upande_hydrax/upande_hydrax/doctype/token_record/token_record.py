# Copyright (c) 2026, edwin@upande.com and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class TokenRecord(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amount_paid: DF.Currency
		closing_balance: DF.Float
		debt_remaining: DF.Currency
		is_preview: DF.Check
		meter: DF.Link | None
		mpesa_receipt_number: DF.Data | None
		receipt_id: DF.Data | None
		repayment_amount: DF.Currency
		token: DF.Data | None
		token_first: DF.Data | None
		token_second: DF.Data | None
		total_unit: DF.Float
		type: DF.Literal["Top Up", "Repayment", "Adjustment"]
	# end: auto-generated types

	_DOCTYPE_NAME = "Token Record"

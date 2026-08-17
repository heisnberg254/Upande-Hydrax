# Copyright (c) 2026, edwin@upande.com and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class DCU(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		dcu_id: DF.Data | None
		dcu_name: DF.Data
		geolocation_sxfh: DF.Geolocation | None
		last_seen: DF.Datetime | None
		latitude: DF.Data | None
		longitude: DF.Data | None
		site_name: DF.Link | None
		status: DF.Literal["Online", "Offline"]
	# end: auto-generated types

	_DOCTYPE_NAME = "DCU"

# Copyright (c) 2026, edwin@upande.com and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class Site(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		geolocation_zkwk: DF.Geolocation | None
		latitude: DF.Data | None
		longitude: DF.Data | None
		site_name: DF.Data | None
	# end: auto-generated types

	_DOCTYPE_NAME = "Site"

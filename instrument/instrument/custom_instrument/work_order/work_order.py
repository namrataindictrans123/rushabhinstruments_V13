from __future__ import unicode_literals
import frappe
import json

@frappe.whitelist()
def check_stock(doc,method):
	if doc.get('__islocal')!= 1:
		final_item_status = []
		final_item_percent = []
		ohs = get_current_stock()
		for item in doc.required_items:
			if item.item_code in ohs:
				if item.required_qty <= ohs.get(item.item_code):
					final_item_status.append('Full Qty Available')
					percent_stock = 100
					final_item_percent.append(percent_stock)
				# elif item.required_qty > ohs.get(item.item_code) and ohs.get(item.item_code) > 0:
				elif item.required_qty > ohs.get(item.item_code) and ohs.get(item.item_code) > 0:
					final_item_status.append('Partial Qty Available')
					percent_stock = (ohs.get(item.item_code)/item.required_qty*100)
					final_item_percent.append(percent_stock)

				else : 
					final_item_status.append('Qty Not Available')
					percent_stock = (ohs.get(item.item_code)/item.required_qty*100)
					final_item_percent.append(percent_stock)

		status_list = ['Full Qty Available']
		status_list_pa = ['Partial Qty Available']
		status_list_na = ['Qty Not Available']
		check =  all(item in status_list for item in final_item_status)
		check_pa = all(item in status_list_pa for item in final_item_status)
		check_na = all(item in status_list_na for item in final_item_status)
		min_value = min(final_item_percent) if len(final_item_percent) > 1 else 0
		if check == True:
			frappe.db.set_value("Work Order",doc.name,'item_stock_status','Full Qty Available')
			frappe.db.set_value("Work Order",doc.name,'stock_percentage',min_value)
			frappe.db.commit()
			doc.reload()
		elif check_pa == True:
			frappe.db.set_value("Work Order",doc.name,'item_stock_status','Partial Qty Available')
			frappe.db.set_value("Work Order",doc.name,'stock_percentage',min_value)
			frappe.db.commit()
			doc.reload()
		elif check_na == True : 
			frappe.db.set_value("Work Order",doc.name,'item_stock_status','Qty Not Available')
			frappe.db.set_value("Work Order",doc.name,'stock_percentage',min_value)
			frappe.db.commit()
			doc.reload()
		elif 'Qty Not Available' in final_item_status and 'Partial Qty Available' in final_item_status: 
			frappe.db.set_value("Work Order",doc.name,'item_stock_status','Qty Available For Some Items')
			frappe.db.set_value("Work Order",doc.name,'stock_percentage',min_value)
			frappe.db.commit()
		else: 
			frappe.db.set_value("Work Order",doc.name,'item_stock_status','Partial Qty Available')
			frappe.db.set_value("Work Order",doc.name,'stock_percentage',min_value)
			frappe.db.commit()
			doc.reload()
	doc.reload()
def get_current_stock():
	# 1.get wip warehouse
	wip_warehouse = frappe.db.get_single_value("Manufacturing Settings", 'default_wip_warehouse')
	current_stock = frappe.db.sql("""SELECT item_code,sum(actual_qty) as qty from `tabBin` where warehouse != '{0}' group by item_code """.format(wip_warehouse),as_dict=1)
	ohs_dict = {item.item_code : item.qty for item in current_stock}
	return ohs_dict

@frappe.whitelist()
def add_bom_level(doc,method):
	if doc.bom_no:
		bom_level = frappe.db.get_value("BOM",{'name' : doc.bom_no},'bom_level')
		if bom_level:
			doc.bom_level = bom_level
			
			# frappe.db.set_value("Work Order",doc.name,'bom_level',bom_level)
			# frappe.db.commit()
			# doc.reload()

@frappe.whitelist()
def on_submit(doc,method):
	if doc.required_items:
		for item in doc.required_items:
			if item.engineering_revision:
				er_rev = frappe.get_doc("Engineering Revision",item.engineering_revision)
				if er_rev :
					if not (er_rev.start_date and er_rev.start_transaction and er_rev.document_type):
						er_rev.start_date = doc.planned_start_date
						er_rev.document_type = "Work Order"
						er_rev.start_transaction = doc.name
					er_rev.last_date = doc.planned_start_date
					er_rev.end_document_type = "Work Order"
					er_rev.end_transaction = doc.name
					er_rev.save(ignore_permissions = True)

@frappe.whitelist()
def get_engineering_revision(item_code,bom_no):
	if item_code:
		engineering_revision = frappe.db.get_value("Item",{'name':item_code},'engineering_revision')
		er_from_bom = frappe.db.get_value("BOM Item",{'parent':bom_no,'item_code':item_code},'engineering_revision')
		if er_from_bom:
			return er_from_bom
		else:
			return engineering_revision

@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_engineering_revisions_for_filter(doctype, txt, searchfield, start, page_len, filters):
	return frappe.db.sql(""" SELECT name FROM `tabEngineering Revision` where item_code = '{0}' """.format(filters.get("item_code")))
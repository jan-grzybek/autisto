from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime


class Database:
    def __init__(self, mongodb):
        self._client = MongoClient(mongodb)
        self._db = self._client["autisto"]
        self._assets = self._db["assets"]
        self._decommissioned = self._db["decommissioned"]
        self.ss = None

    def get_assets(self):
        return self._assets.find({})

    def get_decommissioned(self):
        return self._decommissioned.find({})

    def _add_assets(self, order):
        if order.id is None:
            document = {
                "item_name": order.item_name,
                "category": order.category,
                "quantity": order.quantity,
                "life_expectancy_months": order.life_expectancy,
                "dates_of_purchase": [order.date.strftime("%d-%m-%Y") for _ in range(order.quantity)],
                "prices": [order.price for _ in range(order.quantity)],
                "decommissioned_id": None
            }
            self._assets.insert_one(document)
        else:
            document = self._assets.find_one({"_id": order.id})
            document.pop("_id")
            document["quantity"] += order.quantity
            index_to_append_at = 0
            for date in document["dates_of_purchase"]:
                if order.date < datetime.strptime(date, "%d-%m-%Y"):
                    break
                index_to_append_at += 1
            document["dates_of_purchase"] = [document["dates_of_purchase"][i] for i in range(index_to_append_at)] + \
                                            [order.date.strftime("%d-%m-%Y") for _ in range(order.quantity)] + \
                                            [document["dates_of_purchase"][i]
                                             for i in range(index_to_append_at, len(document["dates_of_purchase"]))]
            document["prices"] = [document["prices"][i] for i in range(index_to_append_at)] + \
                                 [order.price for _ in range(order.quantity)] + \
                                 [document["prices"][i] for i in range(index_to_append_at, len(document["prices"]))]
            self._assets.update_one({"_id": order.id}, {"$set": document})

    def _remove_assets(self, order):
        asset_document = self._assets.find_one({"_id": order.id})
        asset_document.pop("_id")
        if asset_document["decommissioned_id"] is None:
            decommissioned_document = self._assets.find_one({"_id": order.id})
            decommissioned_document.pop("decommissioned_id")
            decommissioned_document["quantity"] = order.quantity
            decommissioned_document["dates_of_purchase"] = asset_document["dates_of_purchase"][:order.quantity]
            decommissioned_document["prices"] = asset_document["prices"][:order.quantity]
            decommissioned_document.pop("_id")
            asset_document["decommissioned_id"] = self._decommissioned.insert_one(decommissioned_document).inserted_id
        else:
            decommissioned_document = self._decommissioned.find_one({"_id": asset_document["decommissioned_id"]})
            decommissioned_document["quantity"] += order.quantity
            decommissioned_document["dates_of_purchase"] += asset_document["dates_of_purchase"][:order.quantity]
            decommissioned_document["prices"] += asset_document["prices"][:order.quantity]
            decommissioned_document.pop("_id")
            self._decommissioned.update_one(
                {"_id": asset_document["decommissioned_id"]}, {"$set": decommissioned_document})
        asset_document["quantity"] -= order.quantity
        if asset_document["quantity"] <= 0:
            self._assets.delete_one({"_id": order.id})
        else:
            asset_document["dates_of_purchase"] = asset_document["dates_of_purchase"][order.quantity:]
            asset_document["prices"] = asset_document["prices"][order.quantity:]
            self._assets.update_one({"_id": order.id}, {"$set": asset_document})

    def get_id_object(self, identifier):
        object_id = ObjectId(identifier)
        if self._assets.find_one({"_id": object_id}) is None:
            raise ValueError
        else:
            return object_id

    def name_already_used(self, item_name):
        return self._assets.find_one({"item_name": item_name}) is not None

    def get_quantity(self, identifier):
        return self._assets.find_one({"_id": ObjectId(identifier)})["quantity"]

    def execute_orders(self, orders):
        for order in orders:
            if order.action == "add":
                self._add_assets(order)
            elif order.action == "remove":
                self._remove_assets(order)
            else:
                raise ValueError
        self.ss.console.clean_up(orders_only=True)
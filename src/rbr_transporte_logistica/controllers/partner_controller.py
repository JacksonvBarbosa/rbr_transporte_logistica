from __future__ import annotations

from typing import Any

from rbr_transporte_logistica.services.partner_service import PartnerService


class PartnerController:
    def __init__(self, service: PartnerService) -> None:
        self.service = service

    def list_partners(self, active_only: bool = False):
        return self.service.list_partners(active_only=active_only)

    def create_partner(self, **payload: Any):
        return self.service.create_partner(**payload)

    def update_partner(self, partner_id: int, **payload: Any):
        return self.service.update_partner(partner_id, **payload)

    def delete_partner(self, partner_id: int) -> None:
        self.service.delete_partner(partner_id)

    def set_partner_active(self, partner_id: int, active: bool):
        return self.service.set_partner_active(partner_id, active)

    def add_rule(self, **payload: Any):
        return self.service.add_rule(**payload)

    def update_rule(self, rule_id: int, **payload: Any):
        return self.service.update_rule(rule_id, **payload)

    def delete_rule(self, rule_id: int) -> None:
        self.service.delete_rule(rule_id)

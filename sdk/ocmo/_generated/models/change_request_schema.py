import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..models.change_request_schema_node_type import ChangeRequestSchemaNodeType
from ..models.change_request_schema_status import ChangeRequestSchemaStatus
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.change_request_approval_event_schema import ChangeRequestApprovalEventSchema
    from ..models.change_request_referrer_schema import ChangeRequestReferrerSchema


T = TypeVar("T", bound="ChangeRequestSchema")


@_attrs_define
class ChangeRequestSchema:
    """
    Attributes:
        path (str):
        node_type (ChangeRequestSchemaNodeType):
        number (int):
        status (ChangeRequestSchemaStatus):
        base_version (int):
        title (str):
        description (str):
        created_by (str):
        created_at (datetime.datetime):
        updated_at (datetime.datetime):
        approvers (List[str]):
        base_superseded (bool):
        latest_version (int):
        approval_count (int):
        required_approvals (int):
        can_apply (bool):
        can_approve (bool):
        can_unapprove (bool):
        projected_version_on_apply (int):
        has_cr_references (bool):
        applied_version (Union[None, Unset, int]):
        applied_by (Union[None, Unset, str]):
        applied_at (Union[None, Unset, datetime.datetime]):
        rejected_reason (Union[Unset, str]):  Default: ''.
        rejected_by (Union[None, Unset, str]):
        rejected_at (Union[None, Unset, datetime.datetime]):
        approval_events (Union[Unset, List['ChangeRequestApprovalEventSchema']]): Approvals in chronological order
        referenced_by (Union[Unset, List['ChangeRequestReferrerSchema']]): Open change requests whose _ocmo metadata
            references this CR
        depends_on (Union[Unset, List['ChangeRequestReferrerSchema']]): Other change requests referenced from this CR's
            _ocmo metadata (@~N)
        issues (Union[Unset, List[str]]): Validation and policy problems that may block apply or safe use
        content (Union[None, Unset, str]):
    """

    path: str
    node_type: ChangeRequestSchemaNodeType
    number: int
    status: ChangeRequestSchemaStatus
    base_version: int
    title: str
    description: str
    created_by: str
    created_at: datetime.datetime
    updated_at: datetime.datetime
    approvers: List[str]
    base_superseded: bool
    latest_version: int
    approval_count: int
    required_approvals: int
    can_apply: bool
    can_approve: bool
    can_unapprove: bool
    projected_version_on_apply: int
    has_cr_references: bool
    applied_version: Union[None, Unset, int] = UNSET
    applied_by: Union[None, Unset, str] = UNSET
    applied_at: Union[None, Unset, datetime.datetime] = UNSET
    rejected_reason: Union[Unset, str] = ""
    rejected_by: Union[None, Unset, str] = UNSET
    rejected_at: Union[None, Unset, datetime.datetime] = UNSET
    approval_events: Union[Unset, List["ChangeRequestApprovalEventSchema"]] = UNSET
    referenced_by: Union[Unset, List["ChangeRequestReferrerSchema"]] = UNSET
    depends_on: Union[Unset, List["ChangeRequestReferrerSchema"]] = UNSET
    issues: Union[Unset, List[str]] = UNSET
    content: Union[None, Unset, str] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        path = self.path

        node_type = self.node_type.value

        number = self.number

        status = self.status.value

        base_version = self.base_version

        title = self.title

        description = self.description

        created_by = self.created_by

        created_at = self.created_at.isoformat()

        updated_at = self.updated_at.isoformat()

        approvers = self.approvers

        base_superseded = self.base_superseded

        latest_version = self.latest_version

        approval_count = self.approval_count

        required_approvals = self.required_approvals

        can_apply = self.can_apply

        can_approve = self.can_approve

        can_unapprove = self.can_unapprove

        projected_version_on_apply = self.projected_version_on_apply

        has_cr_references = self.has_cr_references

        applied_version: Union[None, Unset, int]
        if isinstance(self.applied_version, Unset):
            applied_version = UNSET
        else:
            applied_version = self.applied_version

        applied_by: Union[None, Unset, str]
        if isinstance(self.applied_by, Unset):
            applied_by = UNSET
        else:
            applied_by = self.applied_by

        applied_at: Union[None, Unset, str]
        if isinstance(self.applied_at, Unset):
            applied_at = UNSET
        elif isinstance(self.applied_at, datetime.datetime):
            applied_at = self.applied_at.isoformat()
        else:
            applied_at = self.applied_at

        rejected_reason = self.rejected_reason

        rejected_by: Union[None, Unset, str]
        if isinstance(self.rejected_by, Unset):
            rejected_by = UNSET
        else:
            rejected_by = self.rejected_by

        rejected_at: Union[None, Unset, str]
        if isinstance(self.rejected_at, Unset):
            rejected_at = UNSET
        elif isinstance(self.rejected_at, datetime.datetime):
            rejected_at = self.rejected_at.isoformat()
        else:
            rejected_at = self.rejected_at

        approval_events: Union[Unset, List[Dict[str, Any]]] = UNSET
        if not isinstance(self.approval_events, Unset):
            approval_events = []
            for approval_events_item_data in self.approval_events:
                approval_events_item = approval_events_item_data.to_dict()
                approval_events.append(approval_events_item)

        referenced_by: Union[Unset, List[Dict[str, Any]]] = UNSET
        if not isinstance(self.referenced_by, Unset):
            referenced_by = []
            for referenced_by_item_data in self.referenced_by:
                referenced_by_item = referenced_by_item_data.to_dict()
                referenced_by.append(referenced_by_item)

        depends_on: Union[Unset, List[Dict[str, Any]]] = UNSET
        if not isinstance(self.depends_on, Unset):
            depends_on = []
            for depends_on_item_data in self.depends_on:
                depends_on_item = depends_on_item_data.to_dict()
                depends_on.append(depends_on_item)

        issues: Union[Unset, List[str]] = UNSET
        if not isinstance(self.issues, Unset):
            issues = self.issues

        content: Union[None, Unset, str]
        if isinstance(self.content, Unset):
            content = UNSET
        else:
            content = self.content

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "path": path,
                "node_type": node_type,
                "number": number,
                "status": status,
                "base_version": base_version,
                "title": title,
                "description": description,
                "created_by": created_by,
                "created_at": created_at,
                "updated_at": updated_at,
                "approvers": approvers,
                "base_superseded": base_superseded,
                "latest_version": latest_version,
                "approval_count": approval_count,
                "required_approvals": required_approvals,
                "can_apply": can_apply,
                "can_approve": can_approve,
                "can_unapprove": can_unapprove,
                "projected_version_on_apply": projected_version_on_apply,
                "has_cr_references": has_cr_references,
            }
        )
        if applied_version is not UNSET:
            field_dict["applied_version"] = applied_version
        if applied_by is not UNSET:
            field_dict["applied_by"] = applied_by
        if applied_at is not UNSET:
            field_dict["applied_at"] = applied_at
        if rejected_reason is not UNSET:
            field_dict["rejected_reason"] = rejected_reason
        if rejected_by is not UNSET:
            field_dict["rejected_by"] = rejected_by
        if rejected_at is not UNSET:
            field_dict["rejected_at"] = rejected_at
        if approval_events is not UNSET:
            field_dict["approval_events"] = approval_events
        if referenced_by is not UNSET:
            field_dict["referenced_by"] = referenced_by
        if depends_on is not UNSET:
            field_dict["depends_on"] = depends_on
        if issues is not UNSET:
            field_dict["issues"] = issues
        if content is not UNSET:
            field_dict["content"] = content

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.change_request_approval_event_schema import ChangeRequestApprovalEventSchema
        from ..models.change_request_referrer_schema import ChangeRequestReferrerSchema

        d = src_dict.copy()
        path = d.pop("path")

        node_type = ChangeRequestSchemaNodeType(d.pop("node_type"))

        number = d.pop("number")

        status = ChangeRequestSchemaStatus(d.pop("status"))

        base_version = d.pop("base_version")

        title = d.pop("title")

        description = d.pop("description")

        created_by = d.pop("created_by")

        created_at = isoparse(d.pop("created_at"))

        updated_at = isoparse(d.pop("updated_at"))

        approvers = cast(List[str], d.pop("approvers"))

        base_superseded = d.pop("base_superseded")

        latest_version = d.pop("latest_version")

        approval_count = d.pop("approval_count")

        required_approvals = d.pop("required_approvals")

        can_apply = d.pop("can_apply")

        can_approve = d.pop("can_approve")

        can_unapprove = d.pop("can_unapprove")

        projected_version_on_apply = d.pop("projected_version_on_apply")

        has_cr_references = d.pop("has_cr_references")

        def _parse_applied_version(data: object) -> Union[None, Unset, int]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, int], data)

        applied_version = _parse_applied_version(d.pop("applied_version", UNSET))

        def _parse_applied_by(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        applied_by = _parse_applied_by(d.pop("applied_by", UNSET))

        def _parse_applied_at(data: object) -> Union[None, Unset, datetime.datetime]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                applied_at_type_0 = isoparse(data)

                return applied_at_type_0
            except:  # noqa: E722
                pass
            return cast(Union[None, Unset, datetime.datetime], data)

        applied_at = _parse_applied_at(d.pop("applied_at", UNSET))

        rejected_reason = d.pop("rejected_reason", UNSET)

        def _parse_rejected_by(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        rejected_by = _parse_rejected_by(d.pop("rejected_by", UNSET))

        def _parse_rejected_at(data: object) -> Union[None, Unset, datetime.datetime]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                rejected_at_type_0 = isoparse(data)

                return rejected_at_type_0
            except:  # noqa: E722
                pass
            return cast(Union[None, Unset, datetime.datetime], data)

        rejected_at = _parse_rejected_at(d.pop("rejected_at", UNSET))

        approval_events = []
        _approval_events = d.pop("approval_events", UNSET)
        for approval_events_item_data in _approval_events or []:
            approval_events_item = ChangeRequestApprovalEventSchema.from_dict(approval_events_item_data)

            approval_events.append(approval_events_item)

        referenced_by = []
        _referenced_by = d.pop("referenced_by", UNSET)
        for referenced_by_item_data in _referenced_by or []:
            referenced_by_item = ChangeRequestReferrerSchema.from_dict(referenced_by_item_data)

            referenced_by.append(referenced_by_item)

        depends_on = []
        _depends_on = d.pop("depends_on", UNSET)
        for depends_on_item_data in _depends_on or []:
            depends_on_item = ChangeRequestReferrerSchema.from_dict(depends_on_item_data)

            depends_on.append(depends_on_item)

        issues = cast(List[str], d.pop("issues", UNSET))

        def _parse_content(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        content = _parse_content(d.pop("content", UNSET))

        change_request_schema = cls(
            path=path,
            node_type=node_type,
            number=number,
            status=status,
            base_version=base_version,
            title=title,
            description=description,
            created_by=created_by,
            created_at=created_at,
            updated_at=updated_at,
            approvers=approvers,
            base_superseded=base_superseded,
            latest_version=latest_version,
            approval_count=approval_count,
            required_approvals=required_approvals,
            can_apply=can_apply,
            can_approve=can_approve,
            can_unapprove=can_unapprove,
            projected_version_on_apply=projected_version_on_apply,
            has_cr_references=has_cr_references,
            applied_version=applied_version,
            applied_by=applied_by,
            applied_at=applied_at,
            rejected_reason=rejected_reason,
            rejected_by=rejected_by,
            rejected_at=rejected_at,
            approval_events=approval_events,
            referenced_by=referenced_by,
            depends_on=depends_on,
            issues=issues,
            content=content,
        )

        change_request_schema.additional_properties = d
        return change_request_schema

    @property
    def additional_keys(self) -> List[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties

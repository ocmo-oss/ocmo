from typing import TYPE_CHECKING, Any, Dict, List, Literal, Type, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.builtin_namespace_paths_schema import BuiltinNamespacePathsSchema
    from ..models.public_auth_schema import PublicAuthSchema
    from ..models.reserved_tags_schema import ReservedTagsSchema


T = TypeVar("T", bound="ProductVersionWithNoticeSchema")


@_attrs_define
class ProductVersionWithNoticeSchema:
    """
    Attributes:
        product (Literal['ocmo']): Product identifier
        version (str): Deployed package version
        license_ (str): SPDX license identifier
        license_name (str): Human-readable license name
        config_metadata_key (str): Top-level YAML key for OCMO config metadata (e.g. _ocmo)
        builtin_namespace_paths (BuiltinNamespacePathsSchema):
        reserved_tags (ReservedTagsSchema):
        auth (PublicAuthSchema): Public OIDC settings for frontend, SDK, and CLI bootstrap.
        notice (Union[None, Unset, str]): Product NOTICE text; included when ``?notice=true``
    """

    product: Literal["ocmo"]
    version: str
    license_: str
    license_name: str
    config_metadata_key: str
    builtin_namespace_paths: "BuiltinNamespacePathsSchema"
    reserved_tags: "ReservedTagsSchema"
    auth: "PublicAuthSchema"
    notice: Union[None, Unset, str] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        product = self.product

        version = self.version

        license_ = self.license_

        license_name = self.license_name

        config_metadata_key = self.config_metadata_key

        builtin_namespace_paths = self.builtin_namespace_paths.to_dict()

        reserved_tags = self.reserved_tags.to_dict()

        auth = self.auth.to_dict()

        notice: Union[None, Unset, str]
        if isinstance(self.notice, Unset):
            notice = UNSET
        else:
            notice = self.notice

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "product": product,
                "version": version,
                "license": license_,
                "license_name": license_name,
                "config_metadata_key": config_metadata_key,
                "builtin_namespace_paths": builtin_namespace_paths,
                "reserved_tags": reserved_tags,
                "auth": auth,
            }
        )
        if notice is not UNSET:
            field_dict["notice"] = notice

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.builtin_namespace_paths_schema import BuiltinNamespacePathsSchema
        from ..models.public_auth_schema import PublicAuthSchema
        from ..models.reserved_tags_schema import ReservedTagsSchema

        d = src_dict.copy()
        product = cast(Literal["ocmo"], d.pop("product"))
        if product != "ocmo":
            raise ValueError(f"product must match const 'ocmo', got '{product}'")

        version = d.pop("version")

        license_ = d.pop("license")

        license_name = d.pop("license_name")

        config_metadata_key = d.pop("config_metadata_key")

        builtin_namespace_paths = BuiltinNamespacePathsSchema.from_dict(d.pop("builtin_namespace_paths"))

        reserved_tags = ReservedTagsSchema.from_dict(d.pop("reserved_tags"))

        auth = PublicAuthSchema.from_dict(d.pop("auth"))

        def _parse_notice(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        notice = _parse_notice(d.pop("notice", UNSET))

        product_version_with_notice_schema = cls(
            product=product,
            version=version,
            license_=license_,
            license_name=license_name,
            config_metadata_key=config_metadata_key,
            builtin_namespace_paths=builtin_namespace_paths,
            reserved_tags=reserved_tags,
            auth=auth,
            notice=notice,
        )

        product_version_with_notice_schema.additional_properties = d
        return product_version_with_notice_schema

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

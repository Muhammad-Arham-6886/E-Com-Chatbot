import enum


class RoleEnum(str, enum.Enum):
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    MANAGER = "MANAGER"
    AGENT = "AGENT"
    VIEWER = "VIEWER"

    @classmethod
    def role_hierarchy(cls) -> dict:
        """Returns numeric hierarchy for role comparison (higher number = higher privilege)."""
        return {
            cls.VIEWER: 10,
            cls.AGENT: 20,
            cls.MANAGER: 30,
            cls.ADMIN: 40,
            cls.OWNER: 50,
        }

    def has_permission(self, required_role: "RoleEnum") -> bool:
        hierarchy = self.role_hierarchy()
        return hierarchy.get(self, 0) >= hierarchy.get(required_role, 0)


class MembershipStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INVITED = "INVITED"
    SUSPENDED = "SUSPENDED"


class PlatformEnum(str, enum.Enum):
    WORDPRESS = "WORDPRESS"
    WOOCOMMERCE = "WOOCOMMERCE"
    SHOPIFY = "SHOPIFY"
    CUSTOM = "CUSTOM"
    UNKNOWN = "UNKNOWN"


class WebsiteStatusEnum(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    PENDING_VERIFICATION = "PENDING_VERIFICATION"


class CrawlJobStatusEnum(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class CrawlPageStatusEnum(str, enum.Enum):
    DISCOVERED = "DISCOVERED"
    CRAWLED = "CRAWLED"
    SKIPPED_ROBOTS = "SKIPPED_ROBOTS"
    FAILED = "FAILED"
    DUPLICATE = "DUPLICATE"


class DocumentStatusEnum(str, enum.Enum):
    RAW = "RAW"
    PROCESSED = "PROCESSED"
    SYNCED = "SYNCED"

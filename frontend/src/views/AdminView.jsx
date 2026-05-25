import { Component, useEffect, useMemo, useRef, useState } from "react";
import { adminGet, adminPatch, adminPost } from "../services/adminApiService";
import {
  AdminBadge,
  AdminButton,
  AdminDataTable,
  AdminDrawer,
  AdminEmptyState,
  AdminFilterChips,
  AdminLoadingSkeleton,
  AdminPageHeader,
  AdminSectionCard,
  AdminStatCard,
  AdminStatusPill,
  Icon,
  cx,
} from "../components/admin/AdminUI";

const NAV_ITEMS = [
  { key: "overview", label: "Tổng quan", icon: "overview" },
  { key: "users", label: "Người dùng", icon: "users" },
  { key: "foods", label: "Thực phẩm", icon: "foods" },
  { key: "food-images", label: "Ảnh món ăn", icon: "image" },
  { key: "recommendation-test", label: "Kiểm tra gợi ý", icon: "test" },
  { key: "meal-plans", label: "Thực đơn", icon: "meal" },
  { key: "system-errors", label: "Lỗi hệ thống", icon: "errors" },
  { key: "settings", label: "Cài đặt", icon: "settings" },
];

const PAGE_META = {
  overview: {
    title: "Tổng quan",
    description: "Theo dõi nhanh tình trạng người dùng, dữ liệu món ăn, ảnh cần duyệt và lỗi vận hành.",
  },
  users: {
    title: "Người dùng",
    description: "Tra cứu tài khoản, trạng thái hoạt động và hồ sơ dinh dưỡng của người dùng.",
  },
  foods: {
    title: "Thực phẩm",
    description: "Quản lý danh sách món ăn gọn hơn, chỉ hiển thị các chỉ số quan trọng trên bảng.",
  },
  "food-images": {
    title: "Ảnh món ăn",
    description: "Duyệt, chỉnh sửa hoặc loại bỏ ảnh món ăn mà không thay đổi pipeline xử lý ảnh.",
  },
  "recommendation-test": {
    title: "Kiểm tra gợi ý",
    description: "Tạo hồ sơ thử nghiệm và xem nhanh kcal, protein, cảnh báo cùng dữ liệu kỹ thuật.",
  },
  "meal-plans": {
    title: "Thực đơn",
    description: "Theo dõi các thực đơn đã tạo và mở chi tiết theo dạng drawer.",
  },
  "system-errors": {
    title: "Lỗi hệ thống",
    description: "Kiểm tra lỗi API gần đây, phân loại mức độ và xử lý lỗi đã kiểm tra.",
  },
  settings: {
    title: "Cài đặt",
    description: "Tổng hợp cấu hình hiển thị và phân bố nhóm món đang dùng trong hệ thống.",
  },
};

const CATEGORY_MAP = {
  starch_grain: "Tinh bột hạt",
  starch_tuber: "Tinh bột củ",
  protein_meat: "Đạm động vật",
  protein_seafood: "Đạm hải sản",
  plant_protein: "Đạm thực vật",
  egg: "Trứng",
  vegetable: "Rau xanh",
  fruit: "Trái cây",
  dairy: "Sữa và chế phẩm",
  healthy_fat_nuts: "Chất béo tốt",
  drink_natural: "Nước uống",
  dessert_sweets: "Tráng miệng",
  other: "Nhóm khác",
};

const CATEGORY_OPTIONS = Object.keys(CATEGORY_MAP);

const STATUS_LABELS = {
  valid: "Đạt mục tiêu",
  minor_adjustment: "Gần đạt",
  major_adjustment: "Cần điều chỉnh",
  invalid: "Chưa tối ưu",
  fallback: "Dự phòng",
  error: "Lỗi",
  failed: "Thất bại",
  ACTIVE: "Đang hoạt động",
  LOCKED: "Bị khóa",
  USER: "Người dùng",
  ADMIN: "Admin",
  SUPER_ADMIN: "Super Admin",
};

const DEFAULT_TEST_FORM = {
  sex: "male",
  age: 22,
  height: 167,
  weight: 48,
  target_weight: 58,
  activity: "moderate",
  diet_type: "balanced",
  budget_level: "standard",
  items_per_meal: 5,
  favorite_foods: "",
  disliked_foods: "",
};

function formatNumber(value, suffix = "") {
  const number = Number(value);
  if (!Number.isFinite(number)) return suffix ? `0${suffix}` : "0";
  return `${number.toLocaleString("vi-VN", { maximumFractionDigits: number % 1 ? 1 : 0 })}${suffix}`;
}

function formatDate(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function asArray(value) {
  return Array.isArray(value) ? value : [];
}

function parseList(value) {
  if (Array.isArray(value)) return value.map((item) => String(item).trim()).filter(Boolean);
  return String(value || "")
    .split(/[;,]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function toNumberOrUndefined(value) {
  if (value === "" || value === null || value === undefined) return undefined;
  const number = Number(value);
  return Number.isFinite(number) ? number : undefined;
}

function getStatusLabel(status) {
  return STATUS_LABELS[status] || STATUS_LABELS[String(status || "").toUpperCase()] || status || "Không rõ";
}

function getImageState(food) {
  const directStatus = normalizeImageStatus(food?.image_status || food?.status);
  if (isRejectedStatus(directStatus)) return { label: "Đã từ chối", status: "rejected" };
  if (isApprovedStatus(directStatus)) return { label: "Ảnh thật", status: "verified_real" };
  const source = food?.image_source_type || "placeholder";
  const verified = Boolean(food?.image_verified);
  if (source === "pexels" && !verified) return { label: "Cần duyệt", status: "pexels_pending" };
  if (verified && source !== "placeholder") return { label: "Ảnh thật", status: "verified_real" };
  if (source === "rejected") return { label: "Đã từ chối", status: "rejected" };
  if (String(food?.image_quality_note || "").toLowerCase().includes("từ chối")) return { label: "Đã từ chối", status: "rejected" };
  if (!food?.image_url) return { label: "Thiếu ảnh", status: "warning" };
  return { label: "Placeholder", status: "pending" };
}

function isValidImageUrl(value) {
  const text = String(value || "").trim();
  if (!text) return true;
  try {
    const url = new URL(text);
    return ["http:", "https:"].includes(url.protocol);
  } catch {
    return false;
  }
}

function getDraftImageStatus(food) {
  const directStatus = normalizeImageStatus(food?.status || food?.image_status);
  if (isApprovedStatus(directStatus)) return "approved";
  if (isRejectedStatus(directStatus)) return "rejected";
  const source = String(food?.image_source_type || "").toLowerCase();
  const note = String(food?.image_quality_note || "").toLowerCase();
  if (food?.image_verified) return "approved";
  if (source === "placeholder" && note.includes("từ chối")) return "rejected";
  if (source === "placeholder" && note.includes("tu choi")) return "rejected";
  if (source === "rejected") return "rejected";
  return "pending";
}

function normalizeImageStatus(status) {
  return String(status || "").toLowerCase().trim();
}

function isApprovedStatus(status) {
  return ["approved", "accepted", "active"].includes(normalizeImageStatus(status));
}

function isRejectedStatus(status) {
  return ["rejected", "declined"].includes(normalizeImageStatus(status));
}

function isPendingStatus(status) {
  return !isApprovedStatus(status) && !isRejectedStatus(status);
}

function isFoodExcluded(food) {
  return Boolean(food?.excluded_from_recommendation || food?.admin_rejected);
}

function getImageStatusMeta(status) {
  if (isApprovedStatus(status)) {
    return {
      label: "Đã duyệt",
      className: "status-approved",
    };
  }

  if (isRejectedStatus(status)) {
    return {
      label: "Đã từ chối",
      className: "status-rejected",
    };
  }

  return {
    label: "Cần duyệt",
    className: "status-pending",
  };
}

function getDraftStatusMeta(status, hasError = false) {
  if (hasError) return { label: "Ảnh lỗi", tone: "red", pillStatus: "error" };
  if (isApprovedStatus(status)) return { label: "Đã duyệt", tone: "emerald", pillStatus: "success" };
  if (isRejectedStatus(status)) return { label: "Đã từ chối", tone: "red", pillStatus: "error" };
  return { label: "Cần duyệt", tone: "amber", pillStatus: "pending" };
}

function getImageSourceLabel(source) {
  const normalized = String(source || "").toLowerCase();
  const labels = {
    pexels: "Pexels",
    upload: "Upload",
    uploaded: "Upload",
    manual_url: "URL thủ công",
    manual: "URL thủ công",
    url: "URL thủ công",
    real: "Ảnh đã duyệt",
    wikimedia: "Wikimedia",
    unsplash: "Unsplash",
    placeholder: "Chưa có nguồn",
    rejected: "Đã từ chối",
  };
  return labels[normalized] || source || "Chưa có nguồn";
}

function buildImagePatch({ food, imageUrl, status, sourceType, qualityNote }) {
  const cleanUrl = String(imageUrl || "").trim();
  const patch = {
    image_url: cleanUrl || null,
    image_alt_vi: food?.image_alt_vi || food?.name || null,
    image_source_type: sourceType || (cleanUrl ? "manual_url" : "placeholder"),
    image_verified: status === "approved",
    image_status: status,
    image_quality_note: String(qualityNote || "").trim() || null,
  };
  if (status === "approved") {
    patch.image_source_type = "real";
    patch.image_quality_note = patch.image_quality_note || "Ảnh món ăn đã được duyệt";
  } else if (status === "rejected") {
    patch.image_source_type = "rejected";
    patch.image_verified = false;
    patch.image_quality_note = patch.image_quality_note || "Ảnh món ăn đã bị từ chối";
  } else {
    patch.image_verified = false;
    patch.image_source_type = cleanUrl ? (sourceType === "real" ? "manual_url" : sourceType || "manual_url") : "placeholder";
  }
  return patch;
}

function buildFoodParams(filters, page, pageSize) {
  return {
    q: filters.q,
    category: filters.category,
    menu_eligible: filters.chip === "eligible" ? true : filters.chip === "not_eligible" ? false : undefined,
    missing_image: filters.chip === "missing_image" || filters.chip === "image_errors",
    has_quality_flags: filters.chip === "quality_flags",
    image_status: filters.chip === "pexels_pending" ? "pexels_pending" : filters.chip === "verified_real" ? "verified_real" : undefined,
    limit: pageSize,
    offset: (page - 1) * pageSize,
  };
}

function applyLocalFoodFilter(items, chip) {
  if (chip === "placeholder") {
    return items.filter((item) => (item.image_source_type || "placeholder") === "placeholder" || (!item.image_verified && item.image_url));
  }
  return items;
}

function FoodThumb({ food, size = "md" }) {
  const [failed, setFailed] = useState(false);
  const sizeClasses = {
    md: "h-12 w-12 rounded-2xl object-cover",
    lg: "h-44 w-full rounded-2xl object-cover",
    preview: "aspect-[16/9] w-full rounded-none object-cover",
    contain: "aspect-[4/3] w-full rounded-2xl object-contain",
  };
  const classes = sizeClasses[size] || sizeClasses.md;
  const iconClass = size === "md" ? "h-5 w-5" : "h-9 w-9";
  if (!food?.image_url || failed) {
    const fallbackFrame = size === "preview"
      ? "relative aspect-[16/9] w-full overflow-hidden rounded-t-[20px] bg-slate-100"
      : size === "contain"
        ? "relative aspect-[4/3] w-full overflow-hidden rounded-2xl bg-slate-100"
        : cx("flex shrink-0 items-center justify-center bg-slate-100 text-slate-400", classes);
    return (
      <div className={fallbackFrame}>
        <div className={cx(size === "preview" || size === "contain" ? "flex h-full w-full items-center justify-center" : "flex h-full w-full items-center justify-center bg-slate-100 text-slate-400")}>
          <Icon name="image" className={iconClass} />
        </div>
      </div>
    );
  }
  if (size === "preview") {
    return (
      <div className="relative aspect-[16/9] w-full overflow-hidden rounded-t-[20px] bg-slate-100">
        <img
          src={food.image_url}
          alt={food.image_alt_vi || food.name || "Ảnh món ăn"}
          title={food.image_alt_vi || food.name}
          className="h-full w-full object-cover"
          loading="lazy"
          onError={() => setFailed(true)}
        />
      </div>
    );
  }
  if (size === "contain") {
    return (
      <div className="relative aspect-[4/3] w-full overflow-hidden rounded-2xl bg-slate-100">
        <img
          src={food.image_url}
          alt={food.image_alt_vi || food.name || "Ảnh món ăn"}
          title={food.image_alt_vi || food.name}
          className="h-full w-full object-contain"
          loading="lazy"
          onError={() => setFailed(true)}
        />
      </div>
    );
  }
  return (
    <img
      src={food.image_url}
      alt={food.image_alt_vi || food.name || "Ảnh món ăn"}
      title={food.image_alt_vi || food.name}
      className={cx("shrink-0 bg-slate-100", classes)}
      loading="lazy"
      onError={() => setFailed(true)}
    />
  );
}

function TextInput({ value, onChange, placeholder, icon = "search", className = "" }) {
  return (
    <div className={cx("relative", className)}>
      <span className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-4 text-slate-400">
        <Icon name={icon} className="h-4 w-4" />
      </span>
      <input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        className="h-12 w-full rounded-2xl border border-slate-200 bg-white py-2 pl-11 pr-4 text-sm font-medium text-slate-800 outline-none transition placeholder:text-slate-400 focus:border-blue-300 focus:ring-4 focus:ring-blue-100"
      />
    </div>
  );
}

function SelectInput({ value, onChange, children, className = "" }) {
  return (
    <select
      value={value}
      onChange={(event) => onChange(event.target.value)}
      className={cx("h-12 rounded-2xl border border-slate-200 bg-white px-4 text-sm font-semibold text-slate-700 outline-none transition focus:border-blue-300 focus:ring-4 focus:ring-blue-100", className)}
    >
      {children}
    </select>
  );
}

class AdminErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    console.error("[AdminView] Render error:", error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-screen items-center justify-center bg-slate-50 p-6">
          <AdminSectionCard title="Không thể hiển thị trang Admin" description="Một thành phần giao diện bị lỗi khi đọc dữ liệu. Hãy tải lại trang để thử lại.">
            <pre className="max-h-40 overflow-auto rounded-2xl bg-slate-950 p-4 text-xs text-red-100">{String(this.state.error || "")}</pre>
            <AdminButton className="mt-4" icon="refresh" onClick={() => window.location.reload()}>
              Tải lại trang
            </AdminButton>
          </AdminSectionCard>
        </div>
      );
    }
    return this.props.children;
  }
}

function OverviewPage({ onNavigate, refreshKey }) {
  const [data, setData] = useState({
    overview: null,
    stats: null,
    pendingImages: null,
    issuePlans: null,
    errors: null,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    Promise.allSettled([
      adminGet("/overview"),
      adminGet("/users/stats"),
      adminGet("/foods", { image_status: "pexels_pending", limit: 1 }),
      adminGet("/meal-plans", { only_errors: true, limit: 1 }),
      adminGet("/system-errors", { limit: 5 }),
    ])
      .then((results) => {
        if (cancelled) return;
        const [overview, stats, pendingImages, issuePlans, errors] = results.map((item) => (item.status === "fulfilled" ? item.value : null));
        if (!overview) {
          setError("Không thể tải số liệu tổng quan.");
        } else {
          setError("");
        }
        setData({ overview, stats, pendingImages, issuePlans, errors });
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [refreshKey]);

  if (loading) return <AdminLoadingSkeleton cards={4} rows={4} />;
  if (error) return <AdminEmptyState icon="errors" title="Không tải được tổng quan" description={error} />;

  const overview = data.overview || {};
  const stats = data.stats || {};
  const pendingImageCount = data.pendingImages?.total ?? 0;
  const issuePlanCount = data.issuePlans?.total ?? 0;
  const issueTotal = pendingImageCount + issuePlanCount + (overview.recent_errors || 0);
  const eligibleRate = overview.total_foods ? Math.round((Number(overview.eligible_foods || 0) / Number(overview.total_foods || 1)) * 100) : null;
  const activeRate = overview.total_users ? Math.round((Number(stats.active_users || 0) / Number(overview.total_users || 1)) * 100) : null;

  const cards = [
    { label: "Người dùng", value: formatNumber(overview.total_users), helper: `${formatNumber(stats.active_users)} đang hoạt động`, icon: "users", tone: "blue" },
    { label: "Món được gợi ý", value: formatNumber(overview.eligible_foods), helper: `${formatNumber(overview.total_foods)} món trong dữ liệu`, icon: "foods", tone: "emerald" },
    { label: "Thực đơn đã tạo", value: formatNumber(overview.total_meal_plans), helper: "Meal plan đã sinh", icon: "meal", tone: "violet" },
    { label: "Cần xử lý", value: formatNumber(issueTotal), helper: "Ảnh, lỗi và thực đơn", icon: issueTotal ? "errors" : "check", tone: issueTotal ? "amber" : "emerald" },
  ];

  return (
    <div className="space-y-6">
      <div className="rounded-[24px] bg-slate-950 p-6 text-white shadow-[0_18px_50px_rgba(15,23,42,0.18)]">
        <div className="flex flex-col gap-6 xl:flex-row xl:items-end xl:justify-between">
          <div className="max-w-2xl">
            <p className="text-sm font-semibold text-sky-200">NutriGain Admin</p>
            <h2 className="mt-3 text-3xl font-extrabold tracking-tight sm:text-4xl">Xin chào, Admin</h2>
            <p className="mt-3 text-sm leading-6 text-slate-300">Theo dõi dữ liệu người dùng, thực phẩm và chất lượng gợi ý trong một không gian gọn, rõ và dễ thao tác.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <AdminButton variant="subtle" icon="image" onClick={() => onNavigate("food-images")}>Duyệt ảnh</AdminButton>
            <AdminButton variant="subtle" icon="test" onClick={() => onNavigate("recommendation-test")}>Kiểm tra gợi ý</AdminButton>
            <AdminButton icon="errors" onClick={() => onNavigate("system-errors")}>Xem lỗi</AdminButton>
          </div>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {cards.map((card) => (
          <AdminStatCard key={card.label} {...card} />
        ))}
      </div>

      <div className="grid gap-6 xl:grid-cols-[1fr_1fr]">
        <AdminSectionCard title="Việc cần xử lý">
          <div className="space-y-3">
            <AttentionRow tone={pendingImageCount ? "amber" : "emerald"} title="Ảnh Pexels chờ duyệt" value={formatNumber(pendingImageCount)} action={() => onNavigate("food-images")} />
            <AttentionRow tone={overview.recent_errors ? "red" : "emerald"} title="Lỗi chưa xử lý" value={formatNumber(overview.recent_errors)} action={() => onNavigate("system-errors")} />
            <AttentionRow tone={issuePlanCount ? "amber" : "emerald"} title="Thực đơn cần điều chỉnh" value={formatNumber(issuePlanCount)} action={() => onNavigate("meal-plans")} />
          </div>
        </AdminSectionCard>

        <AdminSectionCard title="Chất lượng hệ thống">
          {eligibleRate !== null || activeRate !== null ? (
            <div className="space-y-5">
              <QualityBar label="Tỷ lệ món được gợi ý" value={eligibleRate} />
              <QualityBar label="Tài khoản đang hoạt động" value={activeRate} />
              <div className="rounded-2xl bg-slate-50 p-4">
                <p className="text-sm font-bold text-slate-900">Phân bố valid/minor/major</p>
                <p className="mt-1 text-sm leading-6 text-slate-500">Chưa có endpoint tổng hợp phân bố trạng thái thực đơn, nên khu vực này chỉ hiển thị khi backend có dữ liệu.</p>
              </div>
            </div>
          ) : (
            <AdminEmptyState icon="overview" title="Chưa có dữ liệu chất lượng" description="Hệ thống chưa có đủ số liệu để hiển thị tỷ lệ vận hành." />
          )}
        </AdminSectionCard>
      </div>
    </div>
  );
}

function AttentionRow({ title, value, tone, action }) {
  const toneClass = {
    amber: "bg-amber-50 text-amber-700",
    emerald: "bg-emerald-50 text-emerald-700",
    red: "bg-red-50 text-red-700",
    blue: "bg-blue-50 text-blue-700",
  }[tone] || "bg-slate-100 text-slate-700";
  return (
    <button type="button" onClick={action} className="flex w-full items-center justify-between gap-4 rounded-2xl border border-slate-100 bg-[#F8FAFC] p-4 text-left transition hover:border-slate-200 hover:bg-white">
      <span className="min-w-0">
        <span className="block truncate text-sm font-bold text-slate-900">{title}</span>
        <span className="mt-1 block text-[13px] text-slate-500">Mở chi tiết</span>
      </span>
      <span className={cx("min-w-12 rounded-full px-3 py-2 text-center text-lg font-extrabold leading-none", toneClass)}>{value}</span>
    </button>
  );
}

function QualityBar({ label, value }) {
  if (value === null || value === undefined) return null;
  return (
    <div>
      <div className="mb-2 flex items-center justify-between gap-3">
        <p className="text-sm font-semibold text-slate-700">{label}</p>
        <p className="text-sm font-extrabold text-slate-950">{value}%</p>
      </div>
      <div className="h-2.5 overflow-hidden rounded-full bg-slate-100">
        <div className="h-full rounded-full bg-blue-600" style={{ width: `${Math.max(0, Math.min(100, value))}%` }} />
      </div>
    </div>
  );
}

function UsersPage({ refreshKey }) {
  const [filters, setFilters] = useState({ q: "", chip: "all" });
  const [data, setData] = useState({ items: [], total: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reloadKey, setReloadKey] = useState(0);
  const [selected, setSelected] = useState(null);
  const [detail, setDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const timer = setTimeout(() => {
      setLoading(true);
      adminGet("/users", {
        q: filters.q,
        status: filters.chip === "active" ? "ACTIVE" : filters.chip === "locked" ? "LOCKED" : undefined,
        limit: 100,
        offset: 0,
      })
        .then((response) => {
          if (cancelled) return;
          setData(response || { items: [], total: 0 });
          setError("");
        })
        .catch((err) => {
          if (!cancelled) setError(err.message || "Không thể tải người dùng.");
        })
        .finally(() => {
          if (!cancelled) setLoading(false);
        });
    }, 250);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [filters.q, filters.chip, refreshKey, reloadKey]);

  const users = useMemo(() => {
    const items = asArray(data.items);
    if (filters.chip === "admin") return items.filter((item) => ["ADMIN", "SUPER_ADMIN"].includes(String(item.role || "").toUpperCase()));
    if (filters.chip === "missing_profile") return items.filter((item) => item.bmi === null || item.bmi === undefined || !item.weight_kg);
    return items;
  }, [data.items, filters.chip]);

  function openUser(user) {
    setSelected(user);
    setDetail(null);
    setDetailLoading(true);
    adminGet(`/users/${user.id}`)
      .then((response) => setDetail(response))
      .catch(() => setDetail(user))
      .finally(() => setDetailLoading(false));
  }

  async function toggleStatus(user) {
    if (!user?.id) return;
    const target = String(user.status || "").toUpperCase() === "LOCKED" ? "ACTIVE" : "LOCKED";
    try {
      await adminPatch(`/users/${user.id}/status`, { status: target });
      setSelected(null);
      setDetail(null);
      setReloadKey((key) => key + 1);
    } catch (err) {
      setError(err.message || "Không thể cập nhật trạng thái người dùng.");
    }
  }

  const chips = [
    { value: "all", label: "Tất cả" },
    { value: "active", label: "Đang hoạt động" },
    { value: "locked", label: "Bị khóa" },
    { value: "admin", label: "Admin" },
    { value: "missing_profile", label: "Thiếu profile" },
  ];

  if (loading) return <AdminLoadingSkeleton rows={6} />;

  return (
    <div className="space-y-5">
      <AdminSectionCard>
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <TextInput className="lg:w-[360px]" value={filters.q} onChange={(q) => setFilters((prev) => ({ ...prev, q }))} placeholder="Tìm người dùng..." />
          <AdminFilterChips items={chips} value={filters.chip} onChange={(chip) => setFilters((prev) => ({ ...prev, chip }))} />
        </div>
      </AdminSectionCard>

      {error ? <AdminEmptyState icon="errors" title="Không tải được người dùng" description={error} /> : null}

      <AdminDataTable
        columns={[
          { key: "user", label: "Người dùng" },
          { key: "status", label: "Trạng thái" },
          { key: "role", label: "Vai trò" },
          { key: "profile", label: "Hồ sơ/BMI" },
          { key: "created", label: "Ngày tạo" },
          { key: "actions", label: "Hành động", align: "right" },
        ]}
        empty={<AdminEmptyState icon="users" title="Không có người dùng" description="Không có tài khoản phù hợp với bộ lọc hiện tại." />}
        minWidth="860px"
      >
        {users.map((user) => (
          <tr key={user.id} className="h-16 transition hover:bg-slate-50">
            <td className="px-5 py-3.5">
              <button type="button" onClick={() => openUser(user)} className="flex min-w-0 items-center gap-3 text-left">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-blue-50 text-sm font-extrabold text-blue-700 ring-1 ring-blue-100">
                  {String(user.full_name || user.email || "U").slice(0, 1).toUpperCase()}
                </span>
                <span className="min-w-0">
                  <span className="block truncate text-sm font-bold text-slate-900" title={user.full_name || user.email}>{user.full_name || "Chưa có tên"}</span>
                  <span className="block max-w-[260px] truncate text-[13px] text-slate-500" title={user.email}>{user.email || `ID #${user.id}`}</span>
                </span>
              </button>
            </td>
            <td className="px-5 py-3.5"><AdminStatusPill status={user.status}>{getStatusLabel(user.status)}</AdminStatusPill></td>
            <td className="px-5 py-3.5"><AdminStatusPill status={user.role}>{getStatusLabel(user.role)}</AdminStatusPill></td>
            <td className="px-5 py-3.5">
              {user.bmi ? (
                <div>
                  <p className="text-sm font-bold text-slate-900">BMI {formatNumber(user.bmi)}</p>
                  <p className="text-[13px] text-slate-500">{user.bmi_label || user.bmi_category || "Đã có profile"}</p>
                </div>
              ) : (
                <AdminBadge tone="amber">Thiếu profile</AdminBadge>
              )}
            </td>
            <td className="px-5 py-3.5 text-sm text-slate-500">{formatDate(user.created_at)}</td>
            <td className="px-5 py-3.5 text-right">
              <AdminButton variant="subtle" className="h-9 px-3 text-xs" onClick={() => openUser(user)}>Mở</AdminButton>
            </td>
          </tr>
        ))}
      </AdminDataTable>

      <UserDetailDrawer user={detail || selected} loading={detailLoading} open={Boolean(selected)} onClose={() => setSelected(null)} onToggleStatus={toggleStatus} />
    </div>
  );
}

function UserDetailDrawer({ user, loading, open, onClose, onToggleStatus }) {
  const profile = user?.profile || {};
  return (
    <AdminDrawer
      open={open}
      onClose={onClose}
      title={user?.full_name || user?.email || "Chi tiết người dùng"}
      subtitle={user?.email}
      footer={
        <div className="flex gap-3">
          <AdminButton variant="subtle" className="flex-1" onClick={onClose}>Đóng</AdminButton>
          <AdminButton className="flex-1" variant={String(user?.status || "").toUpperCase() === "LOCKED" ? "success" : "danger"} icon="lock" onClick={() => onToggleStatus(user)}>
            {String(user?.status || "").toUpperCase() === "LOCKED" ? "Mở khóa" : "Khóa"}
          </AdminButton>
        </div>
      }
    >
      {loading ? (
        <AdminLoadingSkeleton rows={5} />
      ) : (
        <div className="space-y-5">
          <div className="grid grid-cols-2 gap-3">
            <MiniInfo label="Trạng thái" value={<AdminStatusPill status={user?.status}>{getStatusLabel(user?.status)}</AdminStatusPill>} />
            <MiniInfo label="Vai trò" value={<AdminStatusPill status={user?.role}>{getStatusLabel(user?.role)}</AdminStatusPill>} />
            <MiniInfo label="BMI" value={user?.bmi ? `${formatNumber(user.bmi)} - ${user.bmi_label || ""}` : "Thiếu profile"} />
            <MiniInfo label="Ngày tạo" value={formatDate(user?.created_at)} />
          </div>

          <AdminSectionCard title="Hồ sơ dinh dưỡng">
            {user?.profile ? (
              <div className="grid gap-3 sm:grid-cols-2">
                <MiniLine label="Cân nặng" value={`${profile.weight_kg || "-"} kg`} />
                <MiniLine label="Mục tiêu" value={`${profile.target_weight_kg || user?.target_weight_kg || "-"} kg`} />
                <MiniLine label="Chiều cao" value={`${profile.height_cm || "-"} cm`} />
                <MiniLine label="Tuổi / giới tính" value={`${profile.age || "-"} / ${profile.gender || profile.sex || "-"}`} />
                <MiniLine label="Hoạt động" value={profile.activity_level || "-"} />
                <MiniLine label="Chế độ ăn" value={profile.diet_type || "-"} />
                <MiniLine label="Số món mỗi bữa" value={profile.items_per_meal || "-"} />
                <MiniLine label="Ngân sách" value={profile.budget_level || "-"} />
              </div>
            ) : (
              <AdminEmptyState icon="users" title="Chưa có profile" description="Người dùng này chưa hoàn tất hồ sơ dinh dưỡng." />
            )}
          </AdminSectionCard>

          <ChipList title="Món yêu thích" items={profile.favorite_foods} empty="Chưa có món yêu thích" />
          <ChipList title="Món loại trừ" items={profile.disliked_foods} empty="Chưa có món loại trừ" />

          <AdminSectionCard title="Theo dõi cân nặng gần đây">
            {asArray(user?.weight_logs).length ? (
              <div className="space-y-2">
                {asArray(user.weight_logs).slice(0, 5).map((log) => (
                  <MiniLine key={log.id || log.log_date} label={log.log_date} value={`${log.weight_kg} kg`} />
                ))}
              </div>
            ) : (
              <AdminEmptyState icon="overview" title="Chưa có log cân nặng" description="Chưa ghi nhận dữ liệu cân nặng gần đây." />
            )}
          </AdminSectionCard>
        </div>
      )}
    </AdminDrawer>
  );
}

function FoodsPage({ refreshKey }) {
  const [filters, setFilters] = useState({ q: "", category: "", chip: "all" });
  const [page, setPage] = useState(1);
  const [data, setData] = useState({ items: [], total: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState(null);
  const [imageFood, setImageFood] = useState(null);
  const [imageToast, setImageToast] = useState(null);
  const imageToastTimerRef = useRef(null);
  const pageSize = 50;

  function notifyImageToast(type, message) {
    if (imageToastTimerRef.current) {
      clearTimeout(imageToastTimerRef.current);
    }
    setImageToast({ type, message });
    imageToastTimerRef.current = setTimeout(() => {
      setImageToast(null);
    }, 3500);
  }

  useEffect(() => () => {
    if (imageToastTimerRef.current) {
      clearTimeout(imageToastTimerRef.current);
    }
  }, []);

  function setChip(chip) {
    setFilters((prev) => ({ ...prev, chip }));
    setPage(1);
  }

  function loadFoods() {
    setLoading(true);
    adminGet("/foods", buildFoodParams(filters, page, pageSize))
      .then((response) => {
        setData(response || { items: [], total: 0 });
        setError("");
      })
      .catch((err) => setError(err.message || "Không thể tải danh sách thực phẩm."))
      .finally(() => setLoading(false));
  }

  function handleImageUpdated(updatedImage) {
    if (!updatedImage) return;
    const updatedId = String(updatedImage.food_id || updatedImage.id || "");
    if (!updatedId) return;

    setData((prev) => ({
      ...prev,
      items: asArray(prev.items).map((item) => {
        const itemId = String(item.food_id || item.id || "");
        if (itemId !== updatedId) return item;
        return {
          ...item,
          ...updatedImage,
          image_url: updatedImage.image_url ?? updatedImage.url ?? item.image_url,
          image_status: updatedImage.status || updatedImage.image_status || item.image_status,
          image_verified:
            typeof updatedImage.image_verified === "boolean" ? updatedImage.image_verified : item.image_verified,
          image_source_type: updatedImage.image_source_type || item.image_source_type,
          image_quality_note: updatedImage.image_quality_note ?? item.image_quality_note,
        };
      }),
    }));

    setImageFood((prev) => {
      if (!prev) return prev;
      const prevId = String(prev.food_id || prev.id || "");
      return prevId === updatedId ? { ...prev, ...updatedImage } : prev;
    });

    setSelected((prev) => {
      if (!prev) return prev;
      const prevId = String(prev.food_id || prev.id || "");
      if (prevId !== updatedId) return prev;
      return {
        ...prev,
        ...updatedImage,
        image_url: updatedImage.image_url ?? updatedImage.url ?? prev.image_url,
        image_status: updatedImage.status || updatedImage.image_status || prev.image_status,
        image_verified:
          typeof updatedImage.image_verified === "boolean" ? updatedImage.image_verified : prev.image_verified,
        image_source_type: updatedImage.image_source_type || prev.image_source_type,
        image_quality_note: updatedImage.image_quality_note ?? prev.image_quality_note,
      };
    });
  }

  useEffect(() => {
    const timer = setTimeout(loadFoods, 250);
    return () => clearTimeout(timer);
  }, [filters.q, filters.category, filters.chip, page, refreshKey]);

  const items = applyLocalFoodFilter(asArray(data.items), filters.chip);
  const totalPages = Math.max(1, Math.ceil((data.total || items.length || 0) / pageSize));
  const chips = [
    { value: "all", label: "Tất cả" },
    { value: "eligible", label: "Được gợi ý" },
    { value: "not_eligible", label: "Không gợi ý" },
    { value: "missing_image", label: "Thiếu ảnh" },
    { value: "verified_real", label: "Ảnh thật" },
    { value: "pexels_pending", label: "Cần duyệt ảnh" },
    { value: "placeholder", label: "Placeholder" },
    { value: "quality_flags", label: "Có cảnh báo dữ liệu" },
  ];

  async function updateFood(food, patch) {
    const id = food?.food_id || food?.id;
    if (!id) return;
    await adminPatch(`/foods/${id}`, patch);
    loadFoods();
  }

  async function excludeFood(food) {
    const id = food?.food_id || food?.id;
    if (!id) return;
    try {
      const result = await adminPost(`/foods/${id}/exclude-from-recommendations`, {
        reason: "Admin loại khỏi thực đơn gợi ý",
      });
      handleImageUpdated(result?.food || result);
      notifyImageToast("success", result?.message || "Đã loại món khỏi gợi ý thực đơn.");
      loadFoods();
    } catch (error) {
      notifyImageToast("error", error.message || "Không thể loại món khỏi gợi ý.");
    }
  }

  async function restoreFood(food) {
    const id = food?.food_id || food?.id;
    if (!id) return;
    try {
      const result = await adminPost(`/foods/${id}/restore-to-recommendations`, {});
      handleImageUpdated(result?.food || result);
      notifyImageToast("success", result?.message || "Đã khôi phục món vào gợi ý.");
      loadFoods();
    } catch (error) {
      notifyImageToast("error", error.message || "Không thể khôi phục món.");
    }
  }

  if (loading) return <AdminLoadingSkeleton rows={7} />;

  return (
    <div className="space-y-5">
      {imageToast ? (
        <div
          className={cx(
            "fixed right-6 top-6 z-[60] max-w-sm rounded-2xl border px-4 py-3 text-sm font-semibold shadow-xl",
            imageToast.type === "error"
              ? "border-red-200 bg-red-50 text-red-700"
              : "border-emerald-200 bg-emerald-50 text-emerald-700"
          )}
        >
          {imageToast.message}
        </div>
      ) : null}
      <AdminSectionCard>
        <div className="space-y-3">
          <div className="flex flex-col gap-3 lg:flex-row">
            <TextInput className="lg:flex-1" value={filters.q} onChange={(q) => { setFilters((prev) => ({ ...prev, q })); setPage(1); }} placeholder="Tìm tên món hoặc thực phẩm..." />
            <SelectInput value={filters.category} onChange={(category) => { setFilters((prev) => ({ ...prev, category })); setPage(1); }} className="lg:w-64">
              <option value="">Tất cả nhóm món</option>
              {CATEGORY_OPTIONS.map((key) => <option key={key} value={key}>{CATEGORY_MAP[key]}</option>)}
            </SelectInput>
          </div>
          <AdminFilterChips items={chips} value={filters.chip} onChange={setChip} />
        </div>
      </AdminSectionCard>

      {error ? <AdminEmptyState icon="errors" title="Không tải được thực phẩm" description={error} /> : null}

      <AdminDataTable
        columns={[
          { key: "food", label: "Món ăn" },
          { key: "nutrition", label: "Dinh dưỡng" },
          { key: "eligible", label: "Gợi ý" },
          { key: "image", label: "Ảnh" },
          { key: "actions", label: "Hành động", align: "right" },
        ]}
        empty={<AdminEmptyState icon="foods" title="Không có món ăn" description="Không có thực phẩm phù hợp với bộ lọc hiện tại." />}
        minWidth="820px"
      >
        {items.map((food) => {
          const imageState = getImageState(food);
          const excluded = isFoodExcluded(food);
          return (
            <tr key={food.food_id || food.id} className="h-16 transition hover:bg-slate-50">
              <td className="px-5 py-3.5">
                <div className="flex min-w-0 items-center gap-3">
                  <FoodThumb food={food} />
                  <div className="min-w-0">
                    <button type="button" onClick={() => setSelected(food)} className="block max-w-[320px] truncate text-left text-sm font-bold text-slate-900 hover:text-blue-700" title={food.name}>
                      {food.name || "Chưa có tên"}
                    </button>
                    <p className="text-[13px] text-slate-500">{CATEGORY_MAP[food.category] || food.category || "Chưa phân nhóm"}</p>
                  </div>
                </div>
              </td>
              <td className="px-5 py-3.5">
                <p className="text-lg font-extrabold leading-none text-slate-950">{formatNumber(food.calories)} kcal</p>
                <p className="mt-1 text-[13px] font-medium text-slate-500">{formatNumber(food.protein, "g")} protein</p>
              </td>
              <td className="px-5 py-3.5">
                <AdminStatusPill status={excluded ? "error" : food.menu_eligible ? "valid" : "invalid"}>
                  {excluded ? "Đã loại khỏi gợi ý" : food.menu_eligible ? "Được gợi ý" : "Tắt gợi ý"}
                </AdminStatusPill>
              </td>
              <td className="px-5 py-3.5"><AdminStatusPill status={imageState.status}>{imageState.label}</AdminStatusPill></td>
              <td className="px-5 py-3.5">
                <div className="flex justify-end gap-2">
                  <AdminButton variant="subtle" className="h-9 px-3 text-xs" onClick={() => setSelected(food)}>Mở</AdminButton>
                  <AdminButton
                    variant={excluded ? "success" : "danger"}
                    className="h-9 px-3 text-xs"
                    onClick={() => excluded ? restoreFood(food) : excludeFood(food)}
                  >
                    {excluded ? "Khôi phục" : "Loại khỏi thực đơn"}
                  </AdminButton>
                </div>
              </td>
            </tr>
          );
        })}
      </AdminDataTable>

      <Pagination page={page} totalPages={totalPages} total={data.total} onPage={setPage} />

      <FoodDetailDrawer
        food={selected}
        open={Boolean(selected)}
        onClose={() => setSelected(null)}
        onToggleEligible={(food) => updateFood(food, { menu_eligible: !food.menu_eligible })}
        onEditImage={(food) => setImageFood(food)}
        onExcludeFood={excludeFood}
        onRestoreFood={restoreFood}
      />
      <FoodImageEditDrawer
        food={imageFood}
        open={Boolean(imageFood)}
        onClose={() => setImageFood(null)}
        onSaved={loadFoods}
        onImageUpdated={handleImageUpdated}
        onFeedback={notifyImageToast}
        onExcludeFood={excludeFood}
        onRestoreFood={restoreFood}
      />
    </div>
  );
}

function FoodDetailDrawer({ food, open, onClose, onToggleEligible, onEditImage, onExcludeFood, onRestoreFood }) {
  const imageState = getImageState(food);
  const excluded = isFoodExcluded(food);
  return (
    <AdminDrawer
      open={open}
      onClose={onClose}
      title={food?.name || "Chi tiết món ăn"}
      subtitle={food?.food_id ? `ID ${food.food_id}` : ""}
      footer={
        <div className="flex gap-3">
          <AdminButton variant="subtle" className="flex-1" onClick={onClose}>Đóng</AdminButton>
          <AdminButton variant="subtle" icon="edit" className="flex-1" onClick={() => onEditImage(food)}>Sửa ảnh</AdminButton>
          <AdminButton className="flex-1" variant={food?.menu_eligible ? "danger" : "success"} onClick={() => onToggleEligible(food)}>
            {food?.menu_eligible ? "Tắt gợi ý" : "Bật gợi ý"}
          </AdminButton>
          <AdminButton className="flex-1" variant={excluded ? "success" : "danger"} onClick={() => excluded ? onRestoreFood(food) : onExcludeFood(food)}>
            {excluded ? "Khôi phục gợi ý" : "Loại khỏi thực đơn"}
          </AdminButton>
        </div>
      }
    >
      <div className="space-y-5">
        <FoodThumb food={food} size="lg" />
        <div className="grid grid-cols-2 gap-3">
          <MiniInfo label="Kcal" value={formatNumber(food?.calories)} />
          <MiniInfo label="Protein" value={formatNumber(food?.protein, "g")} />
          <MiniInfo label="Fat" value={formatNumber(food?.fat, "g")} />
          <MiniInfo label="Carbs" value={formatNumber(food?.carbs, "g")} />
        </div>
        <AdminSectionCard title="Thông tin chi tiết">
          <div className="space-y-3">
            <MiniLine label="Nhóm món" value={CATEGORY_MAP[food?.category] || food?.category || "-"} />
            <MiniLine label="Khẩu phần" value={food?.serving || food?.serving_display || "-"} />
            <MiniLine label="Serving gợi ý" value={food?.recommended_serving_g ? `${food.recommended_serving_g}g` : "-"} />
            <MiniLine
              label="Gợi ý thực đơn"
              value={<AdminStatusPill status={excluded ? "error" : food?.menu_eligible ? "valid" : "invalid"}>{excluded ? "Đã loại khỏi thực đơn" : food?.menu_eligible ? "Được gợi ý" : "Tắt gợi ý"}</AdminStatusPill>}
            />
            <MiniLine label="Trạng thái ảnh" value={<AdminStatusPill status={imageState.status}>{imageState.label}</AdminStatusPill>} />
          </div>
        </AdminSectionCard>
        {food?.quality_flags ? (
          <AdminSectionCard title="Cảnh báo dữ liệu">
            <p className="rounded-2xl bg-amber-50 p-4 text-sm leading-6 text-amber-800">{food.quality_flags}</p>
          </AdminSectionCard>
        ) : null}
      </div>
    </AdminDrawer>
  );
}

function FoodImagesPage({ refreshKey }) {
  const [tab, setTab] = useState("pending");
  const [page, setPage] = useState(1);
  const [data, setData] = useState({ items: [], total: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [imageFood, setImageFood] = useState(null);
  const [imageToast, setImageToast] = useState(null);
  const imageToastTimerRef = useRef(null);
  const pageSize = 100;

  function notifyImageToast(type, message) {
    if (imageToastTimerRef.current) {
      clearTimeout(imageToastTimerRef.current);
    }
    setImageToast({ type, message });
    imageToastTimerRef.current = setTimeout(() => {
      setImageToast(null);
    }, 3500);
  }

  useEffect(() => () => {
    if (imageToastTimerRef.current) {
      clearTimeout(imageToastTimerRef.current);
    }
  }, []);

  function changeTab(nextTab) {
    setTab(nextTab);
    setPage(1);
  }

  function buildImageParams(nextTab, nextPage) {
    const base = { limit: pageSize, offset: (nextPage - 1) * pageSize };
    if (nextTab === "pending") return { ...base, image_status: "pexels_pending" };
    if (nextTab === "real") return { ...base, image_status: "verified_real" };
    if (nextTab === "placeholder") return { ...base };
    if (nextTab === "errors") return { ...base, missing_image: true };
    return base;
  }

  function loadImages() {
    setLoading(true);
    adminGet("/foods", buildImageParams(tab, page))
      .then((response) => {
        setData(response || { items: [], total: 0 });
        setError("");
      })
      .catch((err) => setError(err.message || "Không thể tải ảnh món ăn."))
      .finally(() => setLoading(false));
  }

  function handleImageUpdated(updatedImage) {
    if (!updatedImage) return;
    const updatedId = String(updatedImage.food_id || updatedImage.id || "");
    if (!updatedId) return;

    setData((prev) => {
      const mappedItems = asArray(prev.items).map((item) => {
        const itemId = String(item.food_id || item.id || "");
        if (itemId !== updatedId) return item;
        return {
          ...item,
          ...updatedImage,
          image_url: updatedImage.image_url ?? updatedImage.url ?? item.image_url,
          image_status: updatedImage.status || updatedImage.image_status || item.image_status,
          image_verified:
            typeof updatedImage.image_verified === "boolean" ? updatedImage.image_verified : item.image_verified,
          image_source_type: updatedImage.image_source_type || item.image_source_type,
          image_quality_note: updatedImage.image_quality_note ?? item.image_quality_note,
        };
      });

      let nextItems = mappedItems;
      if (tab === "pending") {
        nextItems = mappedItems.filter((item) => getImageState(item).status === "pexels_pending");
      } else if (tab === "real") {
        nextItems = mappedItems.filter((item) => getImageState(item).status === "verified_real");
      } else if (tab === "errors") {
        nextItems = mappedItems.filter((item) => !item?.image_url);
      }

      return {
        ...prev,
        items: nextItems,
        total: tab === "placeholder" ? prev.total : nextItems.length,
      };
    });

    setImageFood((prev) => {
      if (!prev) return prev;
      const prevId = String(prev.food_id || prev.id || "");
      if (prevId !== updatedId) return prev;
      return {
        ...prev,
        ...updatedImage,
        image_url: updatedImage.image_url ?? updatedImage.url ?? prev.image_url,
        image_status: updatedImage.status || updatedImage.image_status || prev.image_status,
        image_verified:
          typeof updatedImage.image_verified === "boolean" ? updatedImage.image_verified : prev.image_verified,
        image_source_type: updatedImage.image_source_type || prev.image_source_type,
        image_quality_note: updatedImage.image_quality_note ?? prev.image_quality_note,
      };
    });
  }

  useEffect(loadImages, [tab, page, refreshKey]);

  const tabs = [
    { value: "pending", label: "Cần duyệt" },
    { value: "real", label: "Ảnh thật" },
    { value: "placeholder", label: "Placeholder" },
    { value: "errors", label: "Lỗi ảnh" },
  ];

  const totalPages = Math.max(1, Math.ceil((data.total || 0) / pageSize));
  const items = tab === "placeholder" ? applyLocalFoodFilter(asArray(data.items), "placeholder") : asArray(data.items);
  const pendingCount = tab === "pending" ? data.total || 0 : 0;

  async function patchImage(food, patch) {
    const id = food?.food_id || food?.id;
    if (!id) return;
    await adminPatch(`/foods/${id}`, patch);
    loadImages();
  }

  function approve(food) {
    patchImage(food, {
      image_url: food.image_url || null,
      image_alt_vi: food.image_alt_vi || food.name || null,
      image_source_type: "real",
      image_verified: true,
      image_quality_note: food.image_quality_note || "Ảnh thật đã kiểm duyệt",
    });
  }

  function reject(food) {
    patchImage(food, {
      image_url: null,
      image_alt_vi: food.image_alt_vi || food.name || null,
      image_source_type: "placeholder",
      image_verified: false,
      image_quality_note: "Ảnh Pexels bị từ chối",
    });
  }

  async function excludeFood(food) {
    const id = food?.food_id || food?.id;
    if (!id) return;
    try {
      const result = await adminPost(`/foods/${id}/exclude-from-recommendations`, {
        reason: "Admin loại khỏi thực đơn gợi ý từ duyệt ảnh",
      });
      handleImageUpdated(result?.food || result);
      loadImages();
      notifyImageToast("success", result?.message || "Đã loại món khỏi gợi ý thực đơn.");
    } catch (error) {
      notifyImageToast("error", error.message || "Không thể loại món khỏi gợi ý.");
    }
  }

  async function restoreFood(food) {
    const id = food?.food_id || food?.id;
    if (!id) return;
    try {
      const result = await adminPost(`/foods/${id}/restore-to-recommendations`, {});
      handleImageUpdated(result?.food || result);
      loadImages();
      notifyImageToast("success", result?.message || "Đã khôi phục món vào gợi ý.");
    } catch (error) {
      notifyImageToast("error", error.message || "Không thể khôi phục món.");
    }
  }

  function findAnother(food) {
    const id = food?.food_id || food?.id;
    if (!id) return;
    adminPost(`/food-images/${id}/refetch`, {})
      .then((result) => {
        handleImageUpdated(result);
        loadImages();
        notifyImageToast("success", "Đã tìm ảnh khác từ Pexels.");
        setImageFood(null);
      })
      .catch((error) => notifyImageToast("error", error.message || "Không thể tìm ảnh khác. Vui lòng thử lại."));
  }

  if (loading) return <AdminLoadingSkeleton rows={6} />;

  return (
    <div className="space-y-5">
      {imageToast ? (
        <div
          className={cx(
            "fixed right-6 top-6 z-[60] max-w-sm rounded-2xl border px-4 py-3 text-sm font-semibold shadow-xl",
            imageToast.type === "error"
              ? "border-red-200 bg-red-50 text-red-700"
              : "border-emerald-200 bg-emerald-50 text-emerald-700"
          )}
        >
          {imageToast.message}
        </div>
      ) : null}
      <AdminSectionCard>
        <div className="space-y-4">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <AdminFilterChips items={tabs} value={tab} onChange={changeTab} />
            <div className="flex items-center gap-3">
              <AdminStatusPill status={tab === "pending" && pendingCount ? "warning" : "valid"}>
                {tab === "pending" ? `${formatNumber(pendingCount)} ảnh chờ duyệt` : `${formatNumber(data.total || 0)} mục`}
              </AdminStatusPill>
            </div>
          </div>
          {tab === "pending" ? <p className="text-sm text-slate-500">Tab này chỉ hiển thị ảnh Pexels chưa duyệt có URL hợp lệ.</p> : null}
        </div>
      </AdminSectionCard>
      {error ? <AdminEmptyState icon="errors" title="Không tải được ảnh món ăn" description={error} /> : null}
      {items.length ? (
        <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
          {items.map((food) => {
            const imageState = getImageState(food);
            const excluded = isFoodExcluded(food);
            return (
              <article key={food.food_id || food.id} className={cx("overflow-hidden rounded-[20px] bg-white shadow-[0_8px_24px_rgba(15,23,42,0.06)] ring-1 ring-slate-200/70 transition hover:-translate-y-0.5 hover:shadow-[0_14px_34px_rgba(15,23,42,0.08)]", excluded && "opacity-70")}>
                <FoodThumb food={food} size="preview" />
                <div className="space-y-4 p-5">
                  <div className="min-w-0">
                    <h3 className="line-clamp-2 min-h-[40px] text-sm font-extrabold leading-5 text-slate-950" title={food.name}>{food.name}</h3>
                    <p className="mt-1 truncate text-[13px] text-slate-500" title={food.image_url || ""}>{food.image_source_type || "placeholder"}</p>
                  </div>
                  <div className="flex items-center justify-between gap-3">
                    <AdminStatusPill status={imageState.status}>{imageState.label}</AdminStatusPill>
                    {excluded ? <AdminStatusPill status="error">Đã loại khỏi thực đơn</AdminStatusPill> : null}
                    <span className="text-xs font-semibold text-slate-400">ID {food.food_id}</span>
                  </div>
                  <div className="grid grid-cols-2 gap-2 xl:grid-cols-4">
                    <AdminButton variant="subtle" className="h-9 px-2 text-xs" onClick={() => setImageFood(food)}>Xem</AdminButton>
                    <AdminButton variant="subtle" className="h-9 px-2 text-xs" onClick={() => setImageFood(food)}>Sửa</AdminButton>
                    <AdminButton variant="success" className="h-9 px-2 text-xs" disabled={!food.image_url} onClick={() => approve(food)}>Duyệt</AdminButton>
                    <AdminButton variant={excluded ? "success" : "danger"} className="h-9 px-2 text-xs" onClick={() => excluded ? restoreFood(food) : excludeFood(food)}>
                      {excluded ? "Khôi phục" : "Loại món"}
                    </AdminButton>
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      ) : (
        <AdminEmptyState icon="image" title="Không có ảnh trong nhóm này" description="Danh sách hiện không có ảnh phù hợp với tab đang chọn." />
      )}
      <Pagination page={page} totalPages={totalPages} total={data.total} onPage={setPage} />
      <FoodImageEditDrawer
        food={imageFood}
        open={Boolean(imageFood)}
        onClose={() => setImageFood(null)}
        onSaved={loadImages}
        onImageUpdated={handleImageUpdated}
        onReject={(food) => reject(food)}
        onFindAnother={(food) => findAnother(food)}
        onFeedback={notifyImageToast}
        onExcludeFood={excludeFood}
        onRestoreFood={restoreFood}
      />
    </div>
  );
}

  function FoodImageEditDrawer({ food, open, onClose, onSaved, onImageUpdated, onReject, onFindAnother, onFeedback, onExcludeFood, onRestoreFood }) {
  const [draftImageUrl, setDraftImageUrl] = useState("");
  const [draftStatus, setDraftStatus] = useState("pending");
  const [draftNote, setDraftNote] = useState("");
  const [isUpdatingStatus, setIsUpdatingStatus] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [imageLoadError, setImageLoadError] = useState(false);
  const [showAdvancedImageOptions, setShowAdvancedImageOptions] = useState(false);
  const [message, setMessage] = useState("");
  const urlInputRef = useRef(null);

  useEffect(() => {
    setDraftImageUrl(food?.image_url || food?.url || "");
    setDraftStatus(food?.status || food?.image_status || getDraftImageStatus(food) || "pending");
    setDraftNote(food?.note || food?.image_quality_note || "");
    setImageLoadError(false);
    setShowAdvancedImageOptions(false);
    setMessage("");
  }, [food?.id, food?.status, food?.image_url, food?.url, food?.note, food?.image_status, food?.image_quality_note]);

  useEffect(() => {
    if (open) return;
    setIsSaving(false);
    setIsUpdatingStatus(false);
    setImageLoadError(false);
    setShowAdvancedImageOptions(false);
    setMessage("");
  }, [open]);

  useEffect(() => {
    setImageLoadError(false);
  }, [draftImageUrl]);

  if (!open || !food) return null;

  const excluded = isFoodExcluded(food);
  const cleanUrl = draftImageUrl.trim();
  const urlIsValid = isValidImageUrl(cleanUrl);
  const currentImage = cleanUrl;
  const hasPreviewError = Boolean(currentImage && imageLoadError);
  const statusMeta = getImageStatusMeta(draftStatus);
  const currentImageSource = food?.image_source_type || (cleanUrl ? "manual_url" : "placeholder");
  const hasChanges =
    cleanUrl !== String(food.image_url || food.url || "").trim() ||
    draftStatus !== String(food?.status || food?.image_status || getDraftImageStatus(food) || "pending") ||
    draftNote !== String(food.note || food.image_quality_note || "");

  function emitFeedback(type, feedbackMessage) {
    setMessage(feedbackMessage);
    onFeedback?.(type, feedbackMessage);
  }

  function buildPayload(nextStatus) {
    return buildImagePatch({
      food,
      imageUrl: cleanUrl,
      status: nextStatus,
      sourceType: currentImageSource,
      qualityNote: draftNote,
    });
  }

  function buildUpdatedImage(payload, result, nextStatus) {
    const merged = {
      ...food,
      ...payload,
      ...(result || {}),
      id: food?.id ?? food?.food_id,
      food_id: food?.food_id ?? food?.id,
      image_url: payload.image_url ?? result?.image_url ?? result?.url ?? (cleanUrl || null),
      status: nextStatus,
      image_status: nextStatus,
    };

    return merged;
  }

  async function handleSaveImageChanges(event) {
    event?.preventDefault?.();
    const id = food?.food_id || food?.id;
    if (!id || isSaving || isUpdatingStatus) return;
    if (cleanUrl && !urlIsValid) {
      emitFeedback("error", "URL ảnh không hợp lệ.");
      return;
    }

    setIsSaving(true);
    setMessage("");
    try {
      const payload = buildPayload(draftStatus);
      console.log("[FOOD IMAGE SAVE PAYLOAD]", id, payload);
      const result = await adminPatch(`/foods/${id}`, payload);
      const updatedImage = buildUpdatedImage(payload, result, draftStatus);

      setDraftStatus(draftStatus);
      setDraftImageUrl(updatedImage.image_url || "");
      setDraftNote(updatedImage.image_quality_note || "");
      setImageLoadError(false);
      onImageUpdated?.(updatedImage);
      onSaved?.();
      emitFeedback("success", "Đã lưu thay đổi ảnh.");
      onClose?.();
    } catch (error) {
      console.error("[FOOD IMAGE SAVE ERROR]", error);
      emitFeedback("error", error.message || "Không thể lưu thay đổi ảnh. Vui lòng thử lại.");
    } finally {
      setIsSaving(false);
    }
  }

  async function handleApproveImage() {
    const id = food?.food_id || food?.id;
    if (!id || isUpdatingStatus || isSaving) return;
    if (cleanUrl && !urlIsValid) {
      emitFeedback("error", "URL ảnh không hợp lệ.");
      return;
    }

    setIsUpdatingStatus(true);
    setMessage("");
    try {
      const payload = buildPayload("approved");
      console.log("[FOOD IMAGE APPROVE SAVE PAYLOAD]", id, payload);
      const result = await adminPatch(`/foods/${id}`, payload);
      const updatedImage = buildUpdatedImage(payload, result, "approved");

      setDraftStatus("approved");
      setDraftImageUrl(updatedImage.image_url || "");
      setDraftNote(updatedImage.image_quality_note || "");
      setImageLoadError(false);
      onImageUpdated?.(updatedImage);
      onSaved?.();
      emitFeedback("success", "Đã duyệt và lưu ảnh.");
      onClose?.();
    } catch (error) {
      console.error("[FOOD IMAGE APPROVE SAVE ERROR]", error);
      emitFeedback("error", error.message || "Không thể duyệt ảnh. Vui lòng thử lại.");
    } finally {
      setIsUpdatingStatus(false);
    }
  }

  async function handleRejectImage() {
    const id = food?.food_id || food?.id;
    if (!id || isUpdatingStatus || isSaving) return;
    if (cleanUrl && !urlIsValid) {
      emitFeedback("error", "URL ảnh không hợp lệ.");
      return;
    }

    setIsUpdatingStatus(true);
    setMessage("");
    try {
      const payload = buildPayload("rejected");
      console.log("[FOOD IMAGE REJECT SAVE PAYLOAD]", id, payload);
      const result = await adminPatch(`/foods/${id}`, payload);
      const updatedImage = buildUpdatedImage(payload, result, "rejected");

      setDraftStatus("rejected");
      setDraftImageUrl(updatedImage.image_url || "");
      setDraftNote(updatedImage.image_quality_note || "");
      setImageLoadError(false);
      onImageUpdated?.(updatedImage);
      onSaved?.();
      emitFeedback("success", "Đã từ chối ảnh.");
      onClose?.();
    } catch (error) {
      console.error("[FOOD IMAGE REJECT SAVE ERROR]", error);
      emitFeedback("error", error.message || "Không thể từ chối ảnh. Vui lòng thử lại.");
    } finally {
      setIsUpdatingStatus(false);
    }
  }

  async function handlePasteImageUrl() {
    try {
      const text = await navigator.clipboard?.readText();
      if (!text) return;
      setDraftImageUrl(text.trim());
      setTimeout(() => urlInputRef.current?.focus(), 0);
      setMessage("");
    } catch {
      emitFeedback("error", "Không thể đọc nội dung clipboard.");
    }
  }

  async function handleCopyImageUrl() {
    if (!cleanUrl) return;
    try {
      await navigator.clipboard?.writeText(cleanUrl);
      emitFeedback("success", "Đã sao chép URL ảnh.");
    } catch {
      emitFeedback("error", "Không thể sao chép URL ảnh.");
    }
  }

  function handleOpenOriginalImage() {
    if (!cleanUrl) return;
    window.open(cleanUrl, "_blank", "noopener,noreferrer");
  }

  function handleChangeImage() {
    setTimeout(() => urlInputRef.current?.focus(), 0);
  }

  const imageStatusBadgeClass =
    statusMeta.className === "status-approved"
      ? "border-emerald-200 bg-emerald-50 text-emerald-700"
      : statusMeta.className === "status-rejected"
        ? "border-red-200 bg-red-50 text-red-700"
        : "border-amber-200 bg-amber-50 text-amber-700";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center px-4 py-4">
      <button type="button" aria-label="Đóng" className="absolute inset-0 bg-slate-950/40 backdrop-blur-sm" onClick={onClose} />
      <section className="relative flex w-[min(820px,calc(100vw-32px))] max-h-[82vh] flex-col overflow-hidden rounded-[24px] bg-white shadow-2xl">
        <header className="flex shrink-0 items-start justify-between gap-4 border-b border-[#e5edf0] px-[22px] py-[18px] bg-white">
          <div className="min-w-0">
            <h3 className="text-xl font-extrabold text-[#081832]">Sửa ảnh món ăn</h3>
            <p className="mt-1 truncate text-sm font-semibold text-slate-500">{food?.name || "Chưa có tên món"}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-slate-100 text-slate-500 transition hover:bg-slate-200 hover:text-slate-800"
            aria-label="Đóng"
          >
            <Icon name="close" className="h-4 w-4" />
          </button>
        </header>

        <div className="flex-1 overflow-y-auto px-[22px] py-[18px]">
          <div className="grid gap-[18px] lg:grid-cols-[minmax(0,1fr)_300px]">
            <section className="space-y-3">
              <div className="image-preview-card">
                <div className="image-preview-frame">
                  {currentImage && !imageLoadError ? (
                    <img
                      src={currentImage}
                      alt={food.image_alt_vi || food.name || "Ảnh món ăn"}
                      onLoad={() => setImageLoadError(false)}
                      onError={() => setImageLoadError(true)}
                    />
                  ) : (
                    <div className="flex h-full w-full flex-col items-center justify-center px-6 text-center">
                      <span className="flex h-12 w-12 items-center justify-center rounded-full bg-white text-red-500 ring-1 ring-red-100">
                        <Icon name="image" className="h-6 w-6" />
                      </span>
                      <p className="mt-4 text-sm font-extrabold text-[#081832]">Không tải được ảnh</p>
                      <p className="mt-1 text-sm font-medium text-slate-500">Không tải được ảnh. Vui lòng kiểm tra URL.</p>
                    </div>
                  )}
                </div>
              </div>

              <div className="image-actions-row">
                <button
                  type="button"
                  onClick={handleOpenOriginalImage}
                  disabled={!cleanUrl}
                  className={cx(
                    "inline-flex h-10 items-center justify-center rounded-xl border px-3 text-sm font-semibold transition",
                    cleanUrl ? "border-slate-200 bg-white text-slate-700 hover:bg-slate-50" : "pointer-events-none border-slate-100 bg-slate-50 text-slate-300"
                  )}
                >
                  Mở ảnh gốc
                </button>
                <AdminButton variant="subtle" className="h-10 px-3" disabled={!cleanUrl} onClick={handleCopyImageUrl}>Sao chép URL</AdminButton>
                <AdminButton variant="subtle" className="h-10 px-3" onClick={handleChangeImage}>Thay ảnh</AdminButton>
              </div>

              <div className="image-url-inline">
                <div className="field-header">
                  <label htmlFor="food-image-url">URL ảnh</label>
                  <AdminButton variant="subtle" className="h-8 px-3 text-xs" onClick={handlePasteImageUrl}>Dán</AdminButton>
                </div>
                <input
                  id="food-image-url"
                  ref={urlInputRef}
                  className={cx("admin-input", cleanUrl && !urlIsValid && "border-red-300 focus:border-red-300 focus:shadow-[0_0_0_4px_rgba(239,68,68,0.12)]")}
                  value={draftImageUrl}
                  onChange={(event) => {
                    setDraftImageUrl(event.target.value);
                    setImageLoadError(false);
                    setMessage("");
                  }}
                  placeholder="https://..."
                />
                <p className="field-hint">Sửa link để thay ảnh, preview sẽ cập nhật theo URL này.</p>
                {!cleanUrl ? (
                  <p className="mt-2 text-xs font-semibold text-slate-500">Nhập URL ảnh mới hoặc chọn ảnh khác.</p>
                ) : !urlIsValid ? (
                  <p className="mt-2 text-xs font-semibold text-red-600">URL ảnh không hợp lệ.</p>
                ) : imageLoadError ? (
                  <p className="mt-2 text-xs font-semibold text-red-600">Không tải được ảnh từ URL này.</p>
                ) : null}
              </div>
            </section>

            <aside className="image-side-panel">
              <div className="compact-card image-status-compact">
                <div className="status-top">
                  <strong className="text-sm font-extrabold text-[#081832]">Trạng thái ảnh</strong>
                  <span className={cx("image-status-badge", imageStatusBadgeClass)}>{statusMeta.label}</span>
                </div>

                <div className="meta-row">
                  <span>ID</span>
                  <strong>#{food?.id || food?.food_id || "-"}</strong>
                </div>

                <div className="meta-row">
                  <span>Nguồn</span>
                  <strong>{getImageSourceLabel(food?.image_source_type || (cleanUrl ? "manual_url" : "placeholder"))}</strong>
                </div>

                <div className="meta-row">
                  <span>Gợi ý</span>
                  <AdminStatusPill status={excluded ? "error" : food?.menu_eligible ? "valid" : "invalid"}>
                    {excluded ? "Đã loại khỏi thực đơn" : food?.menu_eligible ? "Được gợi ý" : "Tắt gợi ý"}
                  </AdminStatusPill>
                </div>
              </div>

              <div className="compact-card space-y-3">
                <div>
                  <p className="text-sm font-extrabold text-[#081832]">Duyệt ảnh</p>
                  <p className="mt-1 text-xs font-semibold text-slate-500">Duyệt xong hệ thống sẽ lưu và đóng cửa sổ.</p>
                </div>

                {isPendingStatus(draftStatus) ? (
                  <div className="approval-actions">
                    <AdminButton
                      variant="success"
                      icon="check"
                      disabled={isSaving || isUpdatingStatus || (cleanUrl ? !urlIsValid : false) || imageLoadError}
                      onClick={handleApproveImage}
                    >
                      {isUpdatingStatus ? "Đang duyệt..." : "Duyệt ảnh"}
                    </AdminButton>
                    <AdminButton
                      variant="subtle"
                      disabled={isSaving || isUpdatingStatus}
                      onClick={handleRejectImage}
                    >
                      {isUpdatingStatus ? "Đang xử lý..." : "Từ chối ảnh"}
                    </AdminButton>
                  </div>
                ) : isApprovedStatus(draftStatus) ? (
                  <p className="text-sm font-semibold text-emerald-700">Ảnh này đã được duyệt.</p>
                ) : (
                  <>
                    <p className="text-sm font-semibold text-red-700">Ảnh này đã bị từ chối.</p>
                    <AdminButton
                      variant="subtle"
                      icon="refresh"
                      disabled={isSaving || isUpdatingStatus}
                      onClick={() => onFindAnother?.(food)}
                    >
                      Tìm ảnh khác
                    </AdminButton>
                    <AdminButton
                      variant="success"
                      icon="check"
                      disabled={isSaving || isUpdatingStatus || (cleanUrl ? !urlIsValid : false) || imageLoadError}
                      onClick={handleApproveImage}
                    >
                      {isUpdatingStatus ? "Đang duyệt..." : "Duyệt lại"}
                    </AdminButton>
                  </>
                )}
              </div>

              <div className="compact-card space-y-3">
                <div>
                  <p className="text-sm font-extrabold text-[#081832]">Thực đơn gợi ý</p>
                  <p className="mt-1 text-xs font-semibold text-slate-500">Loại món sẽ chặn recommender chọn món này cho thực đơn mới.</p>
                </div>
                <AdminButton
                  variant={excluded ? "success" : "danger"}
                  disabled={isSaving || isUpdatingStatus}
                  onClick={() => excluded ? onRestoreFood?.(food) : onExcludeFood?.(food)}
                >
                  {excluded ? "Khôi phục gợi ý" : "Loại món khỏi gợi ý"}
                </AdminButton>
              </div>

              <div className="compact-card">
                <button
                  type="button"
                  className="advanced-toggle"
                  onClick={() => setShowAdvancedImageOptions((value) => !value)}
                  aria-expanded={showAdvancedImageOptions}
                >
                  <span>Tùy chọn nâng cao</span>
                  <span className={cx("transition-transform", showAdvancedImageOptions && "rotate-180")}>⌄</span>
                </button>

                {showAdvancedImageOptions ? (
                  <div className="advanced-panel">
                    <div>
                      <label htmlFor="food-image-note" className="mb-2 block text-sm font-extrabold text-[#081832]">Ghi chú ảnh</label>
                      <textarea
                        id="food-image-note"
                        className="admin-input min-h-[88px] resize-none py-3"
                        value={draftNote}
                        onChange={(event) => {
                          setDraftNote(event.target.value);
                          setMessage("");
                        }}
                        placeholder="Ghi chú nội bộ cho ảnh này..."
                      />
                    </div>
                  </div>
                ) : null}
              </div>

              {message ? (
                <p className={cx("rounded-2xl px-4 py-3 text-sm font-semibold", message.includes("Không") || message.includes("không") || message.includes("lỗi") ? "bg-red-50 text-red-700" : "bg-emerald-50 text-emerald-700")}>{message}</p>
              ) : null}
            </aside>
          </div>
        </div>

        <footer className="image-editor-footer">
          <AdminButton variant="subtle" disabled={isSaving || isUpdatingStatus} onClick={onClose}>Đóng</AdminButton>
          <AdminButton
            icon="check"
            disabled={isSaving || isUpdatingStatus || (!hasChanges && !showAdvancedImageOptions) || (cleanUrl ? !urlIsValid : false) || imageLoadError}
            onClick={handleSaveImageChanges}
          >
            {isSaving ? "Đang lưu..." : "Lưu thay đổi"}
          </AdminButton>
        </footer>
      </section>
    </div>
  );
}

function RecommendationTestPage({ refreshKey }) {
  const [form, setForm] = useState(DEFAULT_TEST_FORM);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    setError("");
  }, [refreshKey]);

  function update(key, value) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function runTest() {
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const payload = {
        weight: toNumberOrUndefined(form.weight),
        height: toNumberOrUndefined(form.height),
        target_weight: toNumberOrUndefined(form.target_weight),
        age: toNumberOrUndefined(form.age),
        sex: form.sex,
        activity: form.activity,
        diet_type: form.diet_type,
        diet_style: form.diet_type,
        budget_level: form.budget_level,
        items_per_meal: toNumberOrUndefined(form.items_per_meal),
        goal_type: "gain",
        meal_complexity: "balanced",
        favorite_foods: parseList(form.favorite_foods),
        disliked_foods: parseList(form.disliked_foods),
        save_user_data: false,
      };
      const response = await adminPost("/recommendation-test", payload);
      setResult(response);
    } catch (err) {
      setError(err.message || "Không thể chạy kiểm tra gợi ý.");
    } finally {
      setLoading(false);
    }
  }

  const target = result?.nutrition_target || {};
  const plan = result?.meal_plan || {};
  const validation = result?.validation || {};
  const warnings = asArray(validation.warnings);
  const infos = asArray(validation.infos);
  const meals = asArray(plan.meals);

  return (
    <div className="grid gap-5 xl:grid-cols-[420px_1fr]">
      <AdminSectionCard title="Hồ sơ test" description="Form gọn để nhập các trường chính của profile.">
        <div className="grid gap-4">
          <div className="grid grid-cols-2 gap-3">
            <FormField label="Giới tính"><SelectInput value={form.sex} onChange={(value) => update("sex", value)}><option value="male">Nam</option><option value="female">Nữ</option></SelectInput></FormField>
            <FormField label="Tuổi"><input className="admin-input" type="number" value={form.age} onChange={(event) => update("age", event.target.value)} /></FormField>
            <FormField label="Chiều cao"><input className="admin-input" type="number" value={form.height} onChange={(event) => update("height", event.target.value)} /></FormField>
            <FormField label="Cân nặng"><input className="admin-input" type="number" value={form.weight} onChange={(event) => update("weight", event.target.value)} /></FormField>
            <FormField label="Cân nặng mục tiêu"><input className="admin-input" type="number" value={form.target_weight} onChange={(event) => update("target_weight", event.target.value)} /></FormField>
            <FormField label="Số món mỗi bữa"><input className="admin-input" type="number" min="1" max="10" value={form.items_per_meal} onChange={(event) => update("items_per_meal", event.target.value)} /></FormField>
          </div>
          <FormField label="Mức vận động">
            <SelectInput value={form.activity} onChange={(value) => update("activity", value)}>
              <option value="sedentary">Ít vận động</option>
              <option value="light">Nhẹ</option>
              <option value="moderate">Vừa</option>
              <option value="active">Cao</option>
            </SelectInput>
          </FormField>
          <FormField label="Chế độ ăn">
            <SelectInput value={form.diet_type} onChange={(value) => update("diet_type", value)}>
              <option value="balanced">Cân bằng</option>
              <option value="vegetarian">Ăn chay</option>
              <option value="high_protein">Giàu protein</option>
            </SelectInput>
          </FormField>
          <FormField label="Ngân sách">
            <SelectInput value={form.budget_level} onChange={(value) => update("budget_level", value)}>
              <option value="standard">Tiêu chuẩn</option>
              <option value="flexible">Linh hoạt</option>
              <option value="saving">Tiết kiệm</option>
            </SelectInput>
          </FormField>
          <FormField label="Món yêu thích"><input className="admin-input" value={form.favorite_foods} onChange={(event) => update("favorite_foods", event.target.value)} placeholder="VD: bò, gà, trứng" /></FormField>
          <FormField label="Món loại trừ"><input className="admin-input" value={form.disliked_foods} onChange={(event) => update("disliked_foods", event.target.value)} placeholder="VD: tôm, mực" /></FormField>
          <AdminButton icon="test" disabled={loading} onClick={runTest}>{loading ? "Đang kiểm tra" : "Chạy kiểm tra"}</AdminButton>
        </div>
      </AdminSectionCard>

      <div className="space-y-5">
        {error ? <AdminEmptyState icon="errors" title="Không chạy được kiểm tra" description={error} /> : null}
        {!result && !loading && !error ? <AdminEmptyState icon="test" title="Chưa có kết quả" description="Nhập hồ sơ test rồi bấm chạy kiểm tra để xem thực đơn gợi ý." /> : null}
        {loading ? <AdminLoadingSkeleton cards={4} rows={4} /> : null}
        {result ? (
          <>
            <AdminSectionCard>
              <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                <div>
                  <p className="text-sm font-semibold text-slate-500">Kết quả kiểm tra</p>
                  <div className="mt-3 flex flex-wrap items-center gap-3">
                    <AdminStatusPill status={validation.status || plan.status}>{getStatusLabel(validation.status || plan.status)}</AdminStatusPill>
                    <AdminBadge tone={validation.is_valid || validation.isValid ? "emerald" : "amber"}>{validation.is_valid || validation.isValid ? "Hợp lệ" : "Cần xem lại"}</AdminBadge>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-3 text-right sm:grid-cols-4">
                  <MiniInfo label="Kcal" value={`${formatNumber(plan.total_kcal)} / ${formatNumber(result.target_kcal || target.calorie_target)}`} />
                  <MiniInfo label="Protein" value={`${formatNumber(plan.total_protein_g, "g")} / ${formatNumber(result.target_protein || target.protein_g, "g")}`} />
                </div>
              </div>
            </AdminSectionCard>

            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              <AdminStatCard label="Kcal mục tiêu" value={formatNumber(result.target_kcal || target.calorie_target)} helper="Từ profile test" icon="overview" tone="blue" />
              <AdminStatCard label="Kcal thực đơn" value={formatNumber(plan.total_kcal)} helper={`Lệch ${formatNumber(result.kcal_delta || validation.kcalDiff || validation.kcal_diff)}`} icon="meal" tone="emerald" />
              <AdminStatCard label="Protein mục tiêu" value={formatNumber(result.target_protein || target.protein_g, "g")} helper="Theo cân nặng" icon="foods" tone="violet" />
              <AdminStatCard label="Protein thực đơn" value={formatNumber(plan.total_protein_g, "g")} helper={`Status: ${getStatusLabel(validation.status || plan.status)}`} icon="check" tone="amber" />
            </div>

            <AdminSectionCard title="Warnings / Infos">
              {!infos.length && !warnings.length ? <AdminEmptyState icon="check" title="Không có cảnh báo" description="Kết quả test không trả về warning hoặc info cần chú ý." /> : null}
              {infos.length ? <MessageList tone="blue" title="Infos" items={infos} /> : null}
              {warnings.length ? <MessageList tone="amber" title="Warnings" items={warnings} /> : null}
            </AdminSectionCard>

            <AdminSectionCard title="Danh sách bữa ăn" description="Mỗi bữa được tách card để dễ đọc hơn bảng dài.">
              <div className="grid gap-4 xl:grid-cols-3">
                {meals.map((meal) => (
                  <div key={meal.meal_type} className="rounded-2xl bg-slate-50 p-4">
                    <div className="mb-3 flex items-center justify-between">
                      <h3 className="text-sm font-extrabold text-slate-900">{meal.meal_type}</h3>
                      <AdminBadge tone="blue">{formatNumber(meal.actual_kcal || meal.total_kcal)} kcal</AdminBadge>
                    </div>
                    <div className="space-y-2">
                      {asArray(meal.items).map((item) => (
                        <div key={item.food_id || item.name} className="rounded-xl bg-white p-3">
                          <p className="truncate text-sm font-bold text-slate-800" title={item.name}>{item.name}</p>
                          <p className="mt-1 text-xs text-slate-500">{formatNumber(item.calories || item.kcal)} kcal - {formatNumber(item.protein, "g")} protein</p>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </AdminSectionCard>

            <AdminSectionCard title="Dữ liệu kỹ thuật">
              <details className="rounded-2xl bg-slate-950 p-4 text-slate-100">
                <summary className="cursor-pointer text-sm font-bold">Xem JSON raw</summary>
                <pre className="mt-4 max-h-[420px] overflow-auto text-xs leading-5">{JSON.stringify(result, null, 2)}</pre>
              </details>
            </AdminSectionCard>
          </>
        ) : null}
      </div>
    </div>
  );
}

function MealPlansPage({ refreshKey }) {
  const [filters, setFilters] = useState({ q: "", status: "", only_errors: false });
  const [data, setData] = useState({ items: [], total: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState(null);
  const [detail, setDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const timer = setTimeout(() => {
      setLoading(true);
      adminGet("/meal-plans", { ...filters, limit: 80 })
        .then((response) => {
          if (cancelled) return;
          setData(response || { items: [], total: 0 });
          setError("");
        })
        .catch((err) => {
          if (!cancelled) setError(err.message || "Không thể tải thực đơn.");
        })
        .finally(() => {
          if (!cancelled) setLoading(false);
        });
    }, 250);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [filters.q, filters.status, filters.only_errors, refreshKey]);

  function openDetail(plan) {
    setSelected(plan);
    setDetail(null);
    setDetailLoading(true);
    adminGet(`/meal-plans/${plan.id}`)
      .then(setDetail)
      .catch(() => setDetail(plan))
      .finally(() => setDetailLoading(false));
  }

  if (loading) return <AdminLoadingSkeleton rows={6} />;

  return (
    <div className="space-y-5">
      <AdminSectionCard>
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
          <TextInput className="lg:w-[360px]" value={filters.q} onChange={(q) => setFilters((prev) => ({ ...prev, q }))} placeholder="Tìm theo email..." />
          <SelectInput value={filters.status} onChange={(status) => setFilters((prev) => ({ ...prev, status }))}>
            <option value="">Tất cả status</option>
            <option value="valid">Đạt mục tiêu</option>
            <option value="minor_adjustment">Gần đạt</option>
            <option value="major_adjustment">Cần điều chỉnh</option>
            <option value="invalid">Chưa tối ưu</option>
          </SelectInput>
          <label className="flex h-12 items-center gap-3 rounded-2xl border border-slate-200 bg-white px-4 text-sm font-semibold text-slate-700">
            <input type="checkbox" checked={filters.only_errors} onChange={(event) => setFilters((prev) => ({ ...prev, only_errors: event.target.checked }))} className="h-4 w-4 rounded border-slate-300 text-blue-600" />
            Chỉ thực đơn lỗi
          </label>
        </div>
      </AdminSectionCard>
      {error ? <AdminEmptyState icon="errors" title="Không tải được thực đơn" description={error} /> : null}
      <AdminDataTable
        columns={[
          { key: "user", label: "User" },
          { key: "created", label: "Ngày tạo" },
          { key: "kcal", label: "Kcal" },
          { key: "protein", label: "Protein" },
          { key: "status", label: "Status" },
          { key: "actions", label: "Hành động", align: "right" },
        ]}
        empty={<AdminEmptyState icon="meal" title="Không có thực đơn" description="Không có meal plan phù hợp với bộ lọc hiện tại." />}
        minWidth="820px"
      >
        {asArray(data.items).map((plan) => (
          <tr key={plan.id} className="h-16 transition hover:bg-slate-50">
            <td className="px-5 py-3.5">
              <p className="truncate text-sm font-bold text-slate-900" title={plan.user_email}>{plan.user_email || `User #${plan.user_id}`}</p>
              <p className="text-[13px] text-slate-500">Plan #{plan.id}</p>
            </td>
            <td className="px-5 py-3.5 text-sm text-slate-500">{formatDate(plan.created_at || plan.plan_date)}</td>
            <td className="px-5 py-3.5 text-lg font-extrabold text-slate-950">{formatNumber(plan.total_kcal || plan.target_kcal)}</td>
            <td className="px-5 py-3.5 text-sm font-semibold text-slate-500">{plan.total_protein_g ? formatNumber(plan.total_protein_g, "g") : "-"}</td>
            <td className="px-5 py-3.5"><AdminStatusPill status={plan.status}>{getStatusLabel(plan.status)}</AdminStatusPill></td>
            <td className="px-5 py-3.5 text-right"><AdminButton variant="subtle" className="h-9 px-3 text-xs" onClick={() => openDetail(plan)}>Mở</AdminButton></td>
          </tr>
        ))}
      </AdminDataTable>
      <MealPlanDrawer plan={detail || selected} loading={detailLoading} open={Boolean(selected)} onClose={() => setSelected(null)} />
    </div>
  );
}

function MealPlanDrawer({ plan, loading, open, onClose }) {
  const meals = asArray(plan?.meals);
  const protein = meals.reduce((sum, meal) => sum + asArray(meal.items).reduce((inner, item) => inner + Number(item.protein || 0), 0), 0);
  return (
    <AdminDrawer open={open} onClose={onClose} title={`Thực đơn #${plan?.id || ""}`} subtitle={plan?.user_email || formatDate(plan?.created_at)}>
      {loading ? (
        <AdminLoadingSkeleton rows={5} />
      ) : (
        <div className="space-y-5">
          <div className="grid grid-cols-2 gap-3">
            <MiniInfo label="Kcal" value={formatNumber(plan?.total_kcal || plan?.target_kcal)} />
            <MiniInfo label="Protein" value={protein ? formatNumber(protein, "g") : "-"} />
            <MiniInfo label="Status" value={<AdminStatusPill status={plan?.status}>{getStatusLabel(plan?.status)}</AdminStatusPill>} />
            <MiniInfo label="Ngày tạo" value={formatDate(plan?.created_at || plan?.plan_date)} />
          </div>
          {meals.length ? (
            meals.map((meal) => (
              <AdminSectionCard key={meal.id || meal.meal_type} title={meal.meal_type || "Bữa ăn"} description={`${formatNumber(meal.total_kcal)} kcal`}>
                <div className="space-y-2">
                  {asArray(meal.items).map((item) => (
                    <div key={item.id || item.food_id} className="rounded-2xl bg-slate-50 p-4">
                      <p className="truncate text-sm font-bold text-slate-900" title={item.name}>{item.name || item.food_id}</p>
                      <p className="mt-1 text-xs text-slate-500">{formatNumber(item.kcal)} kcal - {formatNumber(item.protein, "g")} protein - {item.serving_display || "khẩu phần chưa rõ"}</p>
                    </div>
                  ))}
                </div>
              </AdminSectionCard>
            ))
          ) : (
            <AdminEmptyState icon="meal" title="Chưa có chi tiết bữa ăn" description="Backend chưa trả danh sách meal items cho thực đơn này." />
          )}
        </div>
      )}
    </AdminDrawer>
  );
}

function SystemErrorsPage({ refreshKey }) {
  const [data, setData] = useState({ items: [], total: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState(null);

  function loadErrors() {
    setLoading(true);
    adminGet("/system-errors", { limit: 80 })
      .then((response) => {
        setData(response || { items: [], total: 0 });
        setError("");
      })
      .catch((err) => setError(err.message || "Không thể tải lỗi hệ thống."))
      .finally(() => setLoading(false));
  }

  useEffect(loadErrors, [refreshKey]);

  async function resolve(errorItem) {
    if (!errorItem?.id) return;
    await adminPatch(`/system-errors/${errorItem.id}/resolve`, {});
    setSelected(null);
    loadErrors();
  }

  if (loading) return <AdminLoadingSkeleton rows={6} />;

  const errorItems = asArray(data.items);
  const todayKey = new Date().toISOString().slice(0, 10);
  const unresolvedCount = errorItems.filter((item) => String(item.status || "").toUpperCase() !== "RESOLVED").length;
  const todayCount = errorItems.filter((item) => String(item.time || "").slice(0, 10) === todayKey).length;
  const endpointCounts = errorItems.reduce((acc, item) => {
    const key = item.endpoint || "Không rõ";
    acc[key] = (acc[key] || 0) + 1;
    return acc;
  }, {});
  const topEndpoint = Object.entries(endpointCounts).sort((a, b) => b[1] - a[1])[0];

  return (
    <div className="space-y-5">
      <div className="grid gap-4 md:grid-cols-3">
        <AdminStatCard label="Lỗi chưa xử lý" value={formatNumber(unresolvedCount)} helper="Trong danh sách gần đây" icon="errors" tone={unresolvedCount ? "red" : "emerald"} />
        <AdminStatCard label="Lỗi hôm nay" value={formatNumber(todayCount)} helper="Theo thời gian server" icon="overview" tone={todayCount ? "amber" : "emerald"} />
        <AdminStatCard label="Endpoint lỗi nhiều" value={topEndpoint ? formatNumber(topEndpoint[1]) : "-"} helper={topEndpoint?.[0] || "Chưa có dữ liệu"} icon="test" tone="blue" />
      </div>
      {error ? <AdminEmptyState icon="errors" title="Không tải được lỗi" description={error} /> : null}
      <AdminDataTable
        columns={[
          { key: "time", label: "Thời gian" },
          { key: "endpoint", label: "Endpoint" },
          { key: "user", label: "User" },
          { key: "type", label: "Loại lỗi" },
          { key: "status", label: "Trạng thái" },
          { key: "actions", label: "Hành động", align: "right" },
        ]}
        empty={<AdminEmptyState icon="errors" title="Không có lỗi hệ thống" description="Danh sách lỗi hiện đang trống." />}
        minWidth="900px"
      >
        {errorItems.map((item) => {
          const severity = inferSeverity(item);
          return (
            <tr key={item.id} className="h-16 transition hover:bg-slate-50">
              <td className="px-5 py-3.5 text-sm text-slate-500">{formatDate(item.time)}</td>
              <td className="max-w-[260px] px-5 py-3.5"><p className="truncate text-sm font-bold text-slate-900" title={item.endpoint}>{item.endpoint || "-"}</p></td>
              <td className="max-w-[220px] px-5 py-3.5"><p className="truncate text-sm text-slate-600" title={item.user_email}>{item.user_email || "-"}</p></td>
              <td className="px-5 py-3.5"><AdminStatusPill status={severity}>{severity}</AdminStatusPill></td>
              <td className="px-5 py-3.5"><AdminStatusPill status={item.status}>{item.status || "OPEN"}</AdminStatusPill></td>
              <td className="px-5 py-3.5 text-right"><AdminButton variant="subtle" className="h-9 px-3 text-xs" onClick={() => setSelected(item)}>Mở</AdminButton></td>
            </tr>
          );
        })}
      </AdminDataTable>

      <AdminDrawer
        open={Boolean(selected)}
        onClose={() => setSelected(null)}
        title="Chi tiết lỗi"
        subtitle={selected?.endpoint}
        footer={
          <div className="flex gap-3">
            <AdminButton variant="subtle" className="flex-1" onClick={() => setSelected(null)}>Đóng</AdminButton>
            <AdminButton className="flex-1" icon="check" onClick={() => resolve(selected)}>Đánh dấu xử lý</AdminButton>
          </div>
        }
      >
        <div className="space-y-4">
          <MiniInfo label="Mức độ" value={<AdminStatusPill status={inferSeverity(selected)}>{inferSeverity(selected)}</AdminStatusPill>} />
          <MiniLine label="Thời gian" value={formatDate(selected?.time)} />
          <MiniLine label="Endpoint" value={selected?.endpoint || "-"} />
          <MiniLine label="User" value={selected?.user_email || "-"} />
          <AdminSectionCard title="Thông báo lỗi">
            <p className="whitespace-pre-wrap rounded-2xl bg-slate-50 p-4 text-sm leading-6 text-slate-700">{selected?.message || selected?.error_type || "Không có mô tả chi tiết."}</p>
          </AdminSectionCard>
        </div>
      </AdminDrawer>
    </div>
  );
}

function SettingsPage({ refreshKey }) {
  const [data, setData] = useState({ items: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    setLoading(true);
    adminGet("/food-categories/summary")
      .then((response) => {
        setData(response || { items: [] });
        setError("");
      })
      .catch((err) => setError(err.message || "Không thể tải nhóm món."))
      .finally(() => setLoading(false));
  }, [refreshKey]);

  if (loading) return <AdminLoadingSkeleton rows={5} />;
  return (
    <div className="space-y-5">
      {error ? <AdminEmptyState icon="errors" title="Không tải được cài đặt" description={error} /> : null}
      <AdminSectionCard title="Nhóm món" description="Tổng hợp số lượng món ăn theo nhóm chuẩn đang được backend sử dụng.">
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {asArray(data.items).map((item) => (
            <div key={item.category} className="rounded-2xl bg-slate-50 p-4">
              <p className="truncate text-sm font-bold text-slate-900">{CATEGORY_MAP[item.category] || item.category}</p>
              <p className="mt-2 text-2xl font-extrabold text-blue-600">{formatNumber(item.count)}</p>
            </div>
          ))}
        </div>
      </AdminSectionCard>
      <AdminSectionCard title="Ghi chú vận hành" description="Các cài đặt backend, auth, recommender và pipeline ảnh không được thay đổi trong redesign này.">
        <div className="grid gap-3 md:grid-cols-3">
          <MiniInfo label="API admin" value="Giữ nguyên" />
          <MiniInfo label="Recommender" value="Không sửa" />
          <MiniInfo label="Ảnh món ăn" value="Chỉ đổi UI" />
        </div>
      </AdminSectionCard>
    </div>
  );
}

function MessageList({ title, items, tone }) {
  const toneClass = tone === "blue" ? "bg-blue-50 text-blue-800" : "bg-amber-50 text-amber-800";
  return (
    <div className="mt-4 space-y-2">
      <p className="text-xs font-bold uppercase tracking-wide text-slate-400">{title}</p>
      {items.map((item, index) => (
        <p key={`${item}-${index}`} className={cx("rounded-2xl p-3 text-sm leading-6", toneClass)}>{item}</p>
      ))}
    </div>
  );
}

function ChipList({ title, items, empty }) {
  const list = parseList(items);
  return (
    <AdminSectionCard title={title}>
      {list.length ? (
        <div className="flex flex-wrap gap-2">
          {list.map((item) => <AdminBadge key={item} tone="blue">{item}</AdminBadge>)}
        </div>
      ) : (
        <p className="text-sm text-slate-500">{empty}</p>
      )}
    </AdminSectionCard>
  );
}

function MiniInfo({ label, value }) {
  return (
    <div className="rounded-2xl border border-slate-100 bg-[#F8FAFC] p-4">
      <p className="text-[12px] font-semibold uppercase tracking-wide text-slate-400">{label}</p>
      <div className="mt-2 text-sm font-bold text-slate-950">{value}</div>
    </div>
  );
}

function MiniLine({ label, value }) {
  return (
    <div className="flex items-center justify-between gap-4 rounded-2xl border border-slate-100 bg-[#F8FAFC] px-4 py-3">
      <span className="text-sm font-medium text-slate-500">{label}</span>
      <span className="min-w-0 truncate text-right text-sm font-bold text-slate-950" title={typeof value === "string" ? value : undefined}>{value}</span>
    </div>
  );
}

function FormField({ label, children }) {
  return (
    <label className="block">
      <span className="mb-2 block text-sm font-bold text-slate-600">{label}</span>
      {children}
    </label>
  );
}

function Pagination({ page, totalPages, total, onPage }) {
  return (
    <div className="flex flex-col gap-3 rounded-[22px] bg-white p-4 shadow-sm ring-1 ring-slate-200/80 sm:flex-row sm:items-center sm:justify-between">
      <p className="text-sm font-semibold text-slate-500">{formatNumber(total)} kết quả - trang {page}/{totalPages}</p>
      <div className="flex gap-2">
        <AdminButton variant="subtle" disabled={page <= 1} onClick={() => onPage(page - 1)}>Trước</AdminButton>
        <AdminButton variant="subtle" disabled={page >= totalPages} onClick={() => onPage(page + 1)}>Sau</AdminButton>
      </div>
    </div>
  );
}

function inferSeverity(errorItem) {
  const text = `${errorItem?.error_type || ""} ${errorItem?.message || ""} ${errorItem?.status || ""}`.toLowerCase();
  if (text.includes("critical") || text.includes("500") || text.includes("traceback")) return "Critical";
  if (text.includes("warning") || text.includes("422") || text.includes("validation")) return "Warning";
  return "Info";
}

function getInitialKey() {
  const raw = window.location.pathname.split("/").filter(Boolean).pop() || "overview";
  if (raw === "admin") return "overview";
  if (raw === "food-categories") return "settings";
  return PAGE_META[raw] ? raw : "overview";
}

export default function AdminView({ user, onLogout }) {
  return (
    <AdminErrorBoundary>
      <AdminShell user={user} onLogout={onLogout} />
    </AdminErrorBoundary>
  );
}

function AdminShell({ user, onLogout }) {
  const [activeKey, setActiveKey] = useState(getInitialKey);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    const sync = () => setActiveKey(getInitialKey());
    window.addEventListener("popstate", sync);
    return () => window.removeEventListener("popstate", sync);
  }, []);

  function navigate(key) {
    const nextKey = PAGE_META[key] ? key : "overview";
    setActiveKey(nextKey);
    setMobileOpen(false);
    window.history.pushState({}, "", `/admin/${nextKey}`);
  }

  const page = useMemo(() => {
    const props = { refreshKey, onNavigate: navigate };
    if (activeKey === "users") return <UsersPage {...props} />;
    if (activeKey === "foods") return <FoodsPage {...props} />;
    if (activeKey === "food-images") return <FoodImagesPage {...props} />;
    if (activeKey === "recommendation-test") return <RecommendationTestPage {...props} />;
    if (activeKey === "meal-plans") return <MealPlansPage {...props} />;
    if (activeKey === "system-errors") return <SystemErrorsPage {...props} />;
    if (activeKey === "settings") return <SettingsPage {...props} />;
    return <OverviewPage {...props} />;
  }, [activeKey, refreshKey]);

  const meta = PAGE_META[activeKey] || PAGE_META.overview;
  const todayLabel = new Date().toLocaleDateString("vi-VN", {
    weekday: "long",
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });

  return (
    <div className="min-h-screen bg-[#F6F8FB] text-slate-900">
      <style>{`
        .admin-input {
          height: 48px;
          width: 100%;
          border-radius: 12px;
          border: 1px solid #E2E8F0;
          background: #FFFFFF;
          padding: 0 14px;
          font-size: 14px;
          font-weight: 600;
          color: #0F172A;
          outline: none;
          transition: border-color 160ms ease, box-shadow 160ms ease;
        }
        .admin-input:focus {
          border-color: #93C5FD;
          box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.12);
        }
      `}</style>
      <AdminSidebar activeKey={activeKey} onNavigate={navigate} onLogout={onLogout} user={user} mobileOpen={mobileOpen} onClose={() => setMobileOpen(false)} />
      <div className="lg:pl-[260px]">
        <header className="sticky top-0 z-30 border-b border-slate-200/70 bg-[#F6F8FB]/90 px-4 py-3 backdrop-blur lg:px-8">
          <div className="mx-auto flex max-w-[1600px] items-center justify-between gap-3">
            <button type="button" onClick={() => setMobileOpen(true)} className="flex h-10 items-center gap-2 rounded-xl bg-white px-3 text-sm font-bold text-slate-700 shadow-sm ring-1 ring-slate-200 lg:hidden">
              <Icon name="overview" className="h-4 w-4" />
              Menu
            </button>
            <div className="hidden min-w-0 lg:block">
              <p className="truncate text-sm font-bold text-slate-900">{meta.title}</p>
              <p className="truncate text-xs font-medium text-slate-500">{todayLabel}</p>
            </div>
            <div className="ml-auto flex items-center gap-2">
              <AdminButton variant="subtle" icon="refresh" onClick={() => setRefreshKey((key) => key + 1)}>Refresh</AdminButton>
              <div className="hidden items-center gap-3 rounded-2xl bg-white px-3 py-2 shadow-sm shadow-slate-200/50 ring-1 ring-slate-200/80 sm:flex">
                <span className="flex h-9 w-9 items-center justify-center rounded-full bg-blue-50 text-sm font-extrabold text-blue-700 ring-1 ring-blue-100">
                  {String(user?.email || "A").slice(0, 1).toUpperCase()}
                </span>
                <div className="min-w-0">
                  <p className="truncate text-sm font-bold text-slate-900">{user?.full_name || "Admin"}</p>
                  <p className="truncate text-xs text-slate-500">{user?.email || "admin@nutrigain.com"}</p>
                </div>
              </div>
            </div>
          </div>
        </header>

        <main className="mx-auto max-w-[1600px] space-y-6 px-4 py-6 lg:px-8 lg:py-8">
          <AdminPageHeader
            eyebrow="Admin dashboard"
            title={meta.title}
            description={meta.description}
            actions={<AdminBadge tone="emerald">System online</AdminBadge>}
          />
          {page}
        </main>
      </div>
    </div>
  );
}

function AdminSidebar({ activeKey, onNavigate, onLogout, user, mobileOpen, onClose }) {
  const sidebar = (
    <aside className="flex h-full w-[260px] flex-col border-r border-slate-200/80 bg-white p-4">
      <div className="mb-7 flex items-center justify-between gap-3 px-2">
        <button type="button" onClick={() => onNavigate("overview")} className="flex min-w-0 items-center gap-3 text-left">
          <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-slate-950 text-lg font-extrabold text-white shadow-[0_8px_18px_rgba(15,23,42,0.16)]">N</span>
          <span className="min-w-0">
            <span className="block truncate text-base font-extrabold tracking-tight text-slate-950">NutriGain</span>
            <span className="block truncate text-xs font-semibold text-slate-500">Admin workspace</span>
          </span>
        </button>
        <button type="button" onClick={onClose} className="flex h-9 w-9 items-center justify-center rounded-full bg-slate-100 text-slate-500 lg:hidden">
          <Icon name="close" className="h-4 w-4" />
        </button>
      </div>

      <nav className="flex-1 space-y-1 overflow-y-auto pr-1">
        {NAV_ITEMS.map((item) => {
          const active = item.key === activeKey;
          return (
            <button
              type="button"
              key={item.key}
              onClick={() => onNavigate(item.key)}
              className={cx(
                "relative flex h-12 w-full items-center gap-3 rounded-xl px-3 text-left text-sm font-semibold transition",
                active ? "bg-slate-950 text-white shadow-[0_10px_22px_rgba(15,23,42,0.12)]" : "text-slate-600 hover:bg-slate-50 hover:text-slate-950"
              )}
            >
              {active ? <span className="absolute left-0 top-1/2 h-6 w-1 -translate-y-1/2 rounded-r-full bg-sky-400" /> : null}
              <Icon name={item.icon} className="h-5 w-5 shrink-0" />
              <span className="truncate">{item.label}</span>
            </button>
          );
        })}
      </nav>

      <div className="mt-5 space-y-3 rounded-[20px] bg-slate-50 p-4 ring-1 ring-slate-200/70">
        <div className="flex min-w-0 items-center gap-3">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-white text-xs font-extrabold text-blue-700 ring-1 ring-slate-200">
            {String(user?.email || "A").slice(0, 1).toUpperCase()}
          </span>
          <div className="min-w-0">
            <p className="truncate text-sm font-bold text-slate-900">{user?.full_name || "Admin"}</p>
            <p className="truncate text-xs text-slate-500">{user?.email || "admin@nutrigain.com"}</p>
          </div>
        </div>
        <AdminButton variant="ghost" icon="logout" className="w-full justify-start" onClick={onLogout}>Đăng xuất</AdminButton>
      </div>
    </aside>
  );

  return (
    <>
      <div className="fixed inset-y-0 left-0 z-40 hidden lg:block">{sidebar}</div>
      {mobileOpen ? (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button type="button" aria-label="Đóng menu" className="absolute inset-0 bg-slate-950/35" onClick={onClose} />
          <div className="relative h-full">{sidebar}</div>
        </div>
      ) : null}
    </>
  );
}

import { useEffect, useMemo, useState, Component } from "react";
import { adminGet, adminPatch, adminPost } from "../services/adminApiService";
import { parseFoodList } from "../utils/foodList";

// ============================================================================
// 1. STATIC CONFIGURATION & DICTIONARIES
// ============================================================================
const navItems = [
  ["overview", "Tổng quan"],
  ["users", "Người dùng"],
  ["foods", "Thực phẩm"],
  ["food-categories", "Nhóm món"],
  ["recommendation-test", "Kiểm tra thuật toán gợi ý"],
  ["meal-plans", "Thực đơn đã tạo"],
  ["system-errors", "Lỗi hệ thống"],
];

const SUBTITLE_MAP = {
  overview: "Giám sát sức khỏe người dùng và đề xuất dinh dưỡng NutriGain.",
  users: "Quản lý hồ sơ sức khỏe và trạng thái kích hoạt của người dùng.",
  foods: "Tra cứu thông tin, giá trị dinh dưỡng và kiểm duyệt đề xuất món ăn.",
  "food-categories": "Phân tích cơ cấu và tỷ lệ số lượng món ăn theo từng nhóm dinh dưỡng.",
  "recommendation-test": "Mô phỏng hồ sơ người dùng và đánh giá kết quả tạo thực đơn.",
  "meal-plans": "Nhật ký theo dõi chất lượng thực đơn đã được khởi tạo thành công.",
  "system-errors": "Tra cứu sự cố hệ thống và xử lý nhanh lỗi API.",
};

const NAV_ICONS = {
  overview: (
    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
      <path strokeLinecap="round" strokeLinejoin="round" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
    </svg>
  ),
  users: (
    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
    </svg>
  ),
  foods: (
    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13" />
    </svg>
  ),
  "food-categories": (
    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
      <path strokeLinecap="round" strokeLinejoin="round" d="M7 7h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
    </svg>
  ),
  "recommendation-test": (
    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
      <path strokeLinecap="round" strokeLinejoin="round" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547" />
    </svg>
  ),
  "meal-plans": (
    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
      <path strokeLinecap="round" strokeLinejoin="round" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
    </svg>
  ),
  "system-errors": (
    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4" />
    </svg>
  ),
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
  dairy: "Sữa & Chế phẩm",
  healthy_fat_nuts: "Chất béo tốt",
  drink_natural: "Nước uống tự nhiên",
  dessert_sweets: "Món tráng miệng",
  other: "Nhóm khác",
};

const categoryOptions = Object.keys(CATEGORY_MAP);

const formatNumber = (num) => {
  if (num === null || num === undefined) return "0";
  return Number(num).toLocaleString("vi-VN");
};

// ============================================================================
// 2. REUSABLE SYSTEM COMPONENTS (Design System tokens)
// ============================================================================

// A. ERROR BOUNDARY
class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }
  componentDidCatch(error, errorInfo) {
    console.error("[AdminErrorBoundary] Caught render crash:", error, errorInfo);
  }
  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-[#F8FAFC] p-6">
          <div className="max-w-md w-full bg-white rounded-2xl border border-[#E5E7EB] p-8 text-center shadow-sm">
            <div className="h-14 w-14 bg-rose-50 rounded-full flex items-center justify-center mx-auto mb-5 text-rose-500 border border-rose-100">
              <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <h2 className="text-lg font-bold text-slate-900 mb-2">Đã xảy ra sự cố hiển thị</h2>
            <p className="text-sm text-slate-500 mb-6 leading-relaxed">
              Một thành phần của giao diện bị lỗi trong lúc tải dữ liệu. Bạn có thể tải lại trang để khắc phục.
            </p>
            <div className="bg-slate-50 rounded-xl p-4 text-left border border-[#E5E7EB] mb-6 max-h-36 overflow-auto">
              <code className="text-xs font-mono text-rose-600 block whitespace-pre-wrap">
                {this.state.error?.toString()}
              </code>
            </div>
            <button
              onClick={() => {
                this.setState({ hasError: false, error: null });
                window.location.reload();
              }}
              className="w-full py-3 px-4 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold rounded-xl transition-all duration-150"
            >
              Tải lại trang quản trị
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

// B. COMPACT LOADING SKELETON
function AdminLoadingState() {
  return (
    <div className="flex min-h-[300px] flex-col items-center justify-center gap-4 rounded-2xl bg-white border border-[#E5E7EB] p-8 shadow-sm">
      <div className="relative flex h-12 w-12 items-center justify-center">
        <span className="h-8 w-8 animate-spin rounded-full border-4 border-slate-100 border-t-emerald-500" />
      </div>
      <div className="text-center space-y-1">
        <p className="text-sm font-bold text-slate-800">Đang đồng bộ dữ liệu</p>
        <p className="text-xs text-slate-400">Vui lòng đợi giây lát...</p>
      </div>
    </div>
  );
}

// C. COMPACT ERROR INFRASTRUCTURE STATE
function AdminErrorState({ message, onRetry }) {
  return (
    <div className="flex min-h-[260px] flex-col items-center justify-center gap-4 rounded-2xl border border-[#E5E7EB] bg-white p-8 text-center shadow-sm">
      <div className="h-12 w-12 bg-rose-50 rounded-full flex items-center justify-center text-rose-500 border border-rose-100">
        <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
      </div>
      <div className="space-y-1 max-w-md">
        <p className="text-sm font-bold text-slate-800">Kết nối máy chủ thất bại</p>
        <p className="text-xs text-slate-400 leading-relaxed">{message || "Có lỗi xảy ra khi tải dữ liệu."}</p>
      </div>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-2 rounded-xl bg-slate-900 hover:bg-slate-800 px-4 py-2 text-xs font-bold text-white transition-all duration-150"
        >
          Kết nối lại
        </button>
      )}
    </div>
  );
}

// D. CLEAN EMPTY STATES
function AdminEmptyState({ message = "Không có kết quả", desc = "Hệ thống chưa ghi nhận dữ liệu cho bộ lọc này.", icon }) {
  return (
    <div className="flex min-h-[240px] flex-col items-center justify-center gap-3 rounded-2xl border border-[#E5E7EB] bg-white p-8 text-center shadow-sm">
      <div className="h-12 w-12 bg-slate-50 rounded-full flex items-center justify-center text-slate-400 border border-slate-100 shadow-inner">
        {icon || (
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
            <path strokeLinecap="round" strokeLinejoin="round" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0a2 2 0 01-2 2H6a2 2 0 01-2-2m16 0V9a2 2 0 00-2-2H6a2 2 0 00-2 2v4h16z" />
          </svg>
        )}
      </div>
      <div className="space-y-1 max-w-xs">
        <p className="text-sm font-bold text-slate-800">{message}</p>
        <p className="text-xs text-slate-400 leading-relaxed">{desc}</p>
      </div>
    </div>
  );
}

// E. STANDARD STAT BADGES
function StatusBadge({ type = "info", children }) {
  const styles = {
    success: "bg-emerald-50 text-emerald-700 border-emerald-100",
    danger: "bg-rose-50 text-rose-700 border-rose-100",
    warning: "bg-amber-50 text-amber-700 border-amber-100",
    info: "bg-blue-50 text-blue-700 border-blue-100",
    neutral: "bg-slate-50 text-slate-600 border-slate-200",
    admin: "bg-purple-50 text-purple-700 border-purple-100",
  }[type] || "bg-slate-50 text-slate-600 border-slate-100";

  return (
    <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 text-xs font-bold rounded-lg border ${styles}`}>
      {children}
    </span>
  );
}

// F. HERO SECTION CARD FOR OVERVIEW
function SectionCard({ title, subtitle, action, children }) {
  return (
    <div className="bg-white rounded-2xl border border-[#E5E7EB] p-5 shadow-sm">
      {(title || subtitle || action) && (
        <div className="flex items-center justify-between gap-4 border-b border-slate-100 pb-3 mb-4">
          <div className="space-y-0.5">
            {title && <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider leading-none">{title}</h3>}
            {subtitle && <p className="text-xs text-slate-400">{subtitle}</p>}
          </div>
          {action && <div>{action}</div>}
        </div>
      )}
      <div>{children}</div>
    </div>
  );
}

// G. GENERAL KPI CARD (Giant and scans in 3 seconds)
function KPIStatCard({ label, value, sub, icon, color = "green" }) {
  const accentColors = {
    green: { bg: "bg-emerald-50 text-emerald-600 border-emerald-100" },
    blue: { bg: "bg-blue-50 text-blue-600 border-blue-100" },
    purple: { bg: "bg-purple-50 text-purple-600 border-purple-100" },
    red: { bg: "bg-rose-50 text-rose-600 border-rose-100" },
  }[color] || { bg: "bg-slate-50 text-slate-600 border-slate-100" };

  return (
    <div className="rounded-2xl border border-[#E5E7EB] bg-white p-6 shadow-sm">
      <div className="flex items-center justify-between">
        <span className="text-xs font-bold text-slate-400">{label}</span>
        <div className={`p-3 rounded-xl ${accentColors.bg}`}>
          {icon}
        </div>
      </div>
      <div className="mt-4">
        <p className="text-5xl font-black text-slate-900 tracking-tight leading-none">
          {formatNumber(value)}
        </p>
        <p className="text-xs text-slate-400 mt-2 font-medium">{sub}</p>
      </div>
    </div>
  );
}

// H. LATERAL DETAIL SLIDE DRAWER (Enterprise-grade, eliminates split screens)
function DetailDrawer({ isOpen, onClose, title, subtitle, children }) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-hidden flex justify-end">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-slate-900/30 backdrop-blur-xs transition-opacity" onClick={onClose} />
      
      {/* Container */}
      <div className="relative w-full max-w-md bg-white h-full flex flex-col shadow-xl animate-slideOver overflow-hidden border-l border-[#E5E7EB]">
        <header className="p-5 border-b border-slate-100 flex justify-between items-center bg-slate-50/50 shrink-0">
          <div className="min-w-0">
            <span className="text-xs font-bold text-emerald-600">Chi tiết hồ sơ</span>
            <h3 className="text-sm font-bold text-slate-900 truncate mt-0.5 leading-none">{title}</h3>
            {subtitle && <p className="text-xs text-slate-400 mt-1 leading-none">{subtitle}</p>}
          </div>
          <button
            onClick={onClose}
            className="h-8 w-8 rounded-full hover:bg-slate-100 flex items-center justify-center text-slate-400 hover:text-slate-700 transition"
          >
            ✕
          </button>
        </header>

        <div className="flex-1 overflow-y-auto p-5 space-y-5">
          {children}
        </div>
      </div>
    </div>
  );
}

// I. FILTER TOOLBAR CONTAINER
function FilterBar({ children }) {
  return (
    <div className="rounded-2xl border border-[#E5E7EB] bg-white p-3 shadow-sm flex flex-col md:flex-row gap-3 items-center justify-between">
      {children}
    </div>
  );
}

// J. TABLE LAYOUT WITH STICKY HEADER
function DataTable({ headers, children }) {
  return (
    <div className="rounded-2xl border border-[#E5E7EB] bg-white shadow-sm overflow-hidden">
      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-slate-50 border-b border-[#E5E7EB] text-xs font-bold text-slate-400">
            <tr>
              {headers.map((h, i) => (
                <th key={i} className={`px-4 py-3 ${h.align === "right" ? "text-right" : h.align === "center" ? "text-center" : ""}`}>
                  {h.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200 text-slate-700 font-medium">
            {children}
          </tbody>
        </table>
      </div>
    </div>
  );
}


// ============================================================================
// 3. PAGE COMPONENT VIEWS (Redesigned with beautiful content boxes)
// ============================================================================

// A. TỔNG QUAN (OVERVIEW)
function OverviewPage({ onNavigate, statsRefreshed, onRefreshStats }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadData = () => {
    setLoading(true);
    adminGet("/overview")
      .then((d) => {
        setData(d);
        setError("");
      })
      .catch((e) => setError(e.message || "Không thể tải số liệu tổng quan."));
  };

  useEffect(() => {
    loadData();
  }, [statsRefreshed]);

  // Fallback rendering while fetching
  useEffect(() => {
    if (data) setLoading(false);
  }, [data]);

  if (loading && !data) return <AdminLoadingState />;
  if (error && !data) return <AdminErrorState message={error} onRetry={loadData} />;

  const validFoodRatio = data?.total_foods ? Math.round((data.eligible_foods / data.total_foods) * 100) : 0;
  const underweightRatio = data?.total_users ? Math.round((data.underweight_users / data.total_users) * 100) : 0;
  const mealPlansPerUser = data?.total_users ? (data.total_meal_plans / data.total_users).toFixed(1) : "0.0";

  // Only 4 main KPIs in the first row
  const cards = [
    {
      label: "Tổng người dùng",
      value: data?.total_users,
      sub: "Đăng ký tài khoản",
      icon: (
        <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
        </svg>
      ),
      color: "green",
    },
    {
      label: "Thực đơn đã tạo",
      value: data?.total_meal_plans,
      sub: "Khởi tạo thành công",
      icon: (
        <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2" />
        </svg>
      ),
      color: "blue",
    },
    {
      label: "Tổng món ăn",
      value: data?.total_foods,
      sub: "Cơ sở dữ liệu",
      icon: (
        <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13" />
        </svg>
      ),
      color: "purple",
    },
    {
      label: "Lỗi hệ thống",
      value: data?.recent_errors,
      sub: data?.recent_errors > 0 ? "Yêu cầu xử lý" : "Vận hành an toàn",
      icon: (
        <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
      ),
      color: data?.recent_errors > 0 ? "red" : "green",
    }
  ];

  const quickActions = [
    {
      title: "Người dùng",
      desc: "Hồ sơ sức khỏe",
      route: "users",
    },
    {
      title: "Kiểm tra gợi ý",
      desc: "Kiểm tra thuật toán",
      route: "recommendation-test",
    },
    {
      title: "Thực đơn",
      desc: "Nhật ký thực đơn",
      route: "meal-plans",
    },
    {
      title: "Lỗi hệ thống",
      desc: "Tra cứu sự cố API",
      route: "system-errors",
    }
  ];

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Welcome Slim Card */}
      <div className="rounded-2xl bg-gradient-to-r from-emerald-600 to-teal-700 p-4 px-6 text-white shadow-sm flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="space-y-1">
          <h2 className="text-lg font-bold tracking-tight">Hệ thống đang hoạt động ổn định.</h2>
          <p className="text-emerald-50 text-xs">
            Theo dõi người dùng, thực đơn, thực phẩm và lỗi hệ thống.
          </p>
        </div>
        <button
          onClick={onRefreshStats}
          className="px-4 py-2 bg-white/10 hover:bg-white/20 active:bg-white/25 text-white rounded-xl font-bold text-sm border border-white/10 transition shrink-0"
        >
          Làm mới
        </button>
      </div>

      {/* KPI Grid (Only 4 main KPIs) */}
      <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
        {cards.map((card, i) => (
          <KPIStatCard
            key={i}
            label={card.label}
            value={card.value}
            sub={card.sub}
            icon={card.icon}
            color={card.color}
          />
        ))}
      </div>

      {/* Attention & Operational Highlights block */}
      <div className="grid gap-6 md:grid-cols-3">
        
        {/* SECTION: CẦN CHÚ Ý */}
        <div className="md:col-span-1">
          <SectionCard title="Cần chú ý" subtitle="Các điểm vận hành cần quản trị kiểm tra">
            <ul className="space-y-3 mt-2 text-xs font-semibold text-slate-700">
              <li className="flex items-start gap-2 pb-2.5 border-b border-slate-100">
                <span className={`h-2 w-2 rounded-full mt-1.5 shrink-0 ${data?.recent_errors > 0 ? "bg-rose-500 animate-pulse" : "bg-emerald-500"}`} />
                <span>
                  {data?.recent_errors > 0 
                    ? `Có ${data.recent_errors} lỗi hệ thống chưa xử lý cần kiểm tra.` 
                    : "Hệ thống vận hành an toàn, không có lỗi cần xử lý."}
                </span>
              </li>
              <li className="flex items-start gap-2 pb-2.5 border-b border-slate-100">
                <span className="h-2 w-2 rounded-full bg-orange-500 mt-1.5 shrink-0" />
                <span>
                  {data?.underweight_users > 0 
                    ? `Có ${data.underweight_users} người dùng trong nhóm thiếu cân cần theo dõi.` 
                    : "Chưa ghi nhận người dùng thiếu cân vượt ngưỡng."}
                </span>
              </li>
              <li className="flex items-start gap-2 pb-2.5 border-b border-slate-100">
                <span className="h-2 w-2 rounded-full bg-emerald-500 mt-1.5 shrink-0" />
                <span>
                  Tỷ lệ thực phẩm khả dụng đạt {validFoodRatio}%. Có {data ? data.total_foods - data.eligible_foods : 0} món ăn bị khóa khỏi thuật toán gợi ý.
                </span>
              </li>
              <li className="flex items-start gap-2">
                <span className="h-2 w-2 rounded-full bg-blue-500 mt-1.5 shrink-0" />
                <span>
                  Đã hỗ trợ khởi tạo thành công {data?.total_meal_plans || 0} thực đơn tăng cân dinh dưỡng cho người dùng.
                </span>
              </li>
            </ul>
          </SectionCard>
        </div>

        {/* Operational Highlights panel */}
        <div className="md:col-span-2">
          <SectionCard title="Thông tin nổi bật" subtitle="Phân bố dữ liệu sức khỏe và tương tác khách hàng">
            <div className="grid gap-4 sm:grid-cols-4 mt-2">
              <div className="bg-slate-50/50 p-4 rounded-xl border border-slate-100 text-slate-700">
                <span className="text-xs text-slate-400 font-bold block">Người dùng mới hôm nay</span>
                <p className="text-xl font-black text-slate-800 mt-1">+{data?.new_users_today || 0}</p>
              </div>

              <div className="bg-slate-50/50 p-4 rounded-xl border border-slate-100 text-slate-700">
                <div className="flex justify-between items-center text-xs font-bold text-slate-400 mb-1">
                  <span>Món ăn hợp lệ</span>
                  <span className="text-emerald-600 font-extrabold">{validFoodRatio}%</span>
                </div>
                <p className="text-xl font-black text-slate-800 mt-1">{data?.eligible_foods || 0}</p>
              </div>

              <div className="bg-slate-50/50 p-4 rounded-xl border border-slate-100 text-slate-700">
                <div className="flex justify-between items-center text-xs font-bold text-slate-400 mb-1">
                  <span>User thiếu cân</span>
                  <span className="text-orange-500 font-extrabold">{underweightRatio}%</span>
                </div>
                <p className="text-xl font-black text-slate-800 mt-1">{data?.underweight_users || 0}</p>
              </div>

              <div className="bg-slate-50/50 p-4 rounded-xl border border-slate-100 text-slate-700">
                <span className="text-xs text-slate-400 font-bold block">Thực đơn / người dùng</span>
                <p className="text-xl font-black text-slate-800 mt-1">{mealPlansPerUser}</p>
              </div>
            </div>
          </SectionCard>
        </div>
      </div>

      {/* Quick navigation actions links */}
      <div className="space-y-3">
        <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Hành động nhanh</h3>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {quickActions.map((act) => (
            <button
              key={act.title}
              onClick={() => onNavigate(act.route)}
              className="rounded-xl border border-[#E5E7EB] bg-white p-4 text-left transition hover:bg-slate-50 flex flex-col justify-between h-[100px]"
            >
              <h4 className="text-sm font-bold text-slate-800 flex items-center gap-1">
                {act.title}
                <svg className="h-3.5 w-3.5 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                </svg>
              </h4>
              <p className="text-xs text-slate-400 mt-1 font-medium">{act.desc}</p>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

// B. NGƯỜI DÙNG (USERS)
function UsersPage() {
  const [filters, setFilters] = useState({ q: "", status: "", bmi_category: "" });
  const [data, setData] = useState({ items: [] });
  const [selected, setSelected] = useState(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadData = () => {
    setLoading(true);
    adminGet("/users", filters)
      .then((d) => {
        setData(d || { items: [] });
        setError("");
      })
      .catch((e) => setError(e.message || "Không thể tải danh sách người dùng"))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    const delayDebounceFn = setTimeout(() => {
      loadData();
    }, 300);
    return () => clearTimeout(delayDebounceFn);
  }, [filters.q, filters.status, filters.bmi_category]);

  async function toggleStatus(user) {
    try {
      const targetStatus = user.status === "LOCKED" ? "ACTIVE" : "LOCKED";
      await adminPatch(`/users/${user.id}/status`, { status: targetStatus });
      loadData();
      if (selected?.id === user.id) {
        setIsDrawerOpen(false);
        setSelected(null);
      }
    } catch (e) {
      alert("Lỗi khi thay đổi trạng thái: " + e.message);
    }
  }

  const items = Array.isArray(data?.items) ? data.items : [];

  return (
    <div className="space-y-5 animate-fadeIn">
      {/* Search and filter bar */}
      <FilterBar>
        <div className="relative w-full md:flex-1">
          <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-slate-400 pointer-events-none">
            <svg className="h-[18px] w-[18px]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </span>
          <input
            type="text"
            value={filters.q}
            onChange={(e) => setFilters((prev) => ({ ...prev, q: e.target.value }))}
            placeholder="Tìm theo email người dùng..."
            className="h-10 w-full pl-9 pr-4 rounded-xl border border-[#E5E7EB] bg-slate-50 text-sm outline-none focus:border-emerald-500 focus:bg-white transition"
          />
        </div>

        <div className="flex w-full md:w-auto items-center justify-end gap-2 shrink-0">
          <select
            className="h-10 rounded-xl border border-[#E5E7EB] bg-white px-3 text-sm font-bold text-slate-600 outline-none hover:bg-slate-50 transition cursor-pointer"
            value={filters.status}
            onChange={(e) => setFilters((prev) => ({ ...prev, status: e.target.value }))}
          >
            <option value="">Tất cả trạng thái</option>
            <option value="ACTIVE">Hoạt động</option>
            <option value="LOCKED">Bị khóa</option>
          </select>

          <select
            className="h-10 rounded-xl border border-[#E5E7EB] bg-white px-3 text-sm font-bold text-slate-600 outline-none hover:bg-slate-50 transition cursor-pointer"
            value={filters.bmi_category}
            onChange={(e) => setFilters((prev) => ({ ...prev, bmi_category: e.target.value }))}
          >
            <option value="">Tất cả nhóm BMI</option>
            <option value="underweight">Thiếu cân</option>
            <option value="normal">Bình thường</option>
            <option value="overweight">Thừa cân</option>
            <option value="obese">Béo phì</option>
          </select>
        </div>
      </FilterBar>

      {loading ? (
        <AdminLoadingState />
      ) : error ? (
        <AdminErrorState message={error} onRetry={loadData} />
      ) : items.length === 0 ? (
        <AdminEmptyState message="Không tìm thấy người dùng phù hợp" />
      ) : (
        <DataTable
          headers={[
            { label: "Người dùng" },
            { label: "Vai trò" },
            { label: "Trạng thái" },
            { label: "Điều phối", align: "right" }
          ]}
        >
          {items.map((user) => {
            const firstLetter = user?.email ? user.email.charAt(0).toUpperCase() : "U";
            return (
              <tr key={user?.id} className="hover:bg-slate-50/40 transition">
                <td className="px-4 py-3 flex items-center gap-3">
                  <div className="h-8 w-8 rounded-full bg-slate-100 text-slate-700 flex items-center justify-center font-bold text-xs shrink-0">
                    {firstLetter}
                  </div>
                  <div className="min-w-0">
                    <div className="font-bold text-slate-800 truncate text-sm">{user?.email}</div>
                    <div className="text-[11px] text-slate-400 mt-0.5">
                      Đăng ký: {user?.created_at?.slice(0, 10)}
                    </div>
                  </div>
                </td>
                <td className="px-4 py-3 align-middle text-sm text-slate-500">
                  {user?.role || "USER"}
                </td>
                <td className="px-4 py-3 align-middle">
                  <StatusBadge type={user?.status === "ACTIVE" ? "success" : "danger"}>
                    {user?.status}
                  </StatusBadge>
                </td>
                <td className="px-4 py-3 align-middle text-right space-x-1">
                  <button
                    onClick={() => {
                      adminGet(`/users/${user.id}`).then((res) => {
                        setSelected(res);
                        setIsDrawerOpen(true);
                      });
                    }}
                    className="h-[30px] rounded-lg bg-slate-50 hover:bg-slate-100 text-xs font-bold text-slate-700 px-3 border border-slate-200 transition animate-click"
                  >
                    Chi tiết
                  </button>
                  <button
                    onClick={() => toggleStatus(user)}
                    className={`h-[30px] rounded-lg px-3 text-xs font-bold text-white transition animate-click ${
                      user?.status === "LOCKED" ? "bg-emerald-600 hover:bg-emerald-700" : "bg-rose-600 hover:bg-rose-700"
                    }`}
                  >
                    {user?.status === "LOCKED" ? "Mở" : "Khóa"}
                  </button>
                </td>
              </tr>
            );
          })}
        </DataTable>
      )}

      {/* Drawer slide detailed view */}
      <DetailDrawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        title={selected?.email}
        subtitle={`Tài khoản ID: #${selected?.id}`}
      >
        {selected && (
          <div className="space-y-4">
            {/* Height and weight indices */}
            <div className="grid grid-cols-2 gap-3 bg-slate-50 p-4 rounded-xl border border-slate-100">
              <div className="space-y-0.5">
                <p className="text-xs text-slate-400 font-bold uppercase">Chiều cao</p>
                <p className="text-base font-bold text-slate-800">{selected.profile?.height_cm || selected.height_cm || "-"} cm</p>
              </div>
              <div className="space-y-0.5">
                <p className="text-xs text-slate-400 font-bold uppercase">Cân nặng</p>
                <p className="text-base font-bold text-slate-800">{selected.profile?.weight_kg || selected.weight_kg || "-"} kg</p>
              </div>
            </div>

            {/* Health parameters list */}
            <div className="space-y-3 bg-white border border-[#E5E7EB] p-4 rounded-xl">
              <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider pb-1.5 border-b border-slate-50">Chỉ số thể chất</h4>
              <ul className="space-y-3 text-xs font-bold text-slate-600">
                <li className="flex justify-between items-center">
                  <span className="text-slate-400">Chỉ số BMI:</span>
                  <span className="text-slate-800 font-extrabold">{selected.bmi || selected.profile?.bmi || "-"}</span>
                </li>
                <li className="flex justify-between items-center">
                  <span className="text-slate-400">Cân nặng mục tiêu:</span>
                  <span className="text-emerald-600 font-black">{selected.profile?.target_weight_kg || "-"} kg</span>
                </li>
                <li className="flex justify-between items-center">
                  <span className="text-slate-400">Tuổi & Giới tính:</span>
                  <span className="text-slate-800">
                    {selected.profile?.age || "-"} tuổi / {selected.profile?.sex === "male" ? "Nam" : "Nữ"}
                  </span>
                </li>
                <li className="flex justify-between items-center">
                  <span className="text-slate-400">Chế độ dinh dưỡng:</span>
                  <span className="text-slate-800 capitalize font-bold">
                    {selected.profile?.diet_type || "-"}
                  </span>
                </li>
              </ul>
            </div>

            {/* Actions for locking or unlocked */}
            <div className="pt-2">
              <button
                onClick={() => toggleStatus(selected)}
                className={`w-full py-2.5 px-4 rounded-xl font-bold text-xs text-white transition ${
                  selected?.status === "LOCKED" ? "bg-emerald-600 hover:bg-emerald-700" : "bg-rose-600 hover:bg-rose-700"
                }`}
              >
                {selected?.status === "LOCKED" ? "Mở khóa tài khoản" : "Khóa tài khoản"}
              </button>
            </div>
          </div>
        )}
      </DetailDrawer>
    </div>
  );
}

// C. THỰC PHẨM (FOODS)
function FoodsPage() {
  const [filters, setFilters] = useState({ q: "", category: "", menu_eligible: "", missing_image: false, has_quality_flags: false });
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [data, setData] = useState({ items: [], total: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const handleFilterChange = (key, value) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
    setPage(1);
  };

  const loadData = () => {
    setLoading(true);
    const offset = (page - 1) * pageSize;
    adminGet("/foods", {
      q: filters.q,
      category: filters.category,
      menu_eligible: filters.menu_eligible,
      missing_image: filters.missing_image,
      has_quality_flags: filters.has_quality_flags,
      limit: pageSize,
      offset: offset,
    })
      .then((d) => {
        setData(d || { items: [], total: 0 });
        setError("");
      })
      .catch((e) => setError(e.message || "Không thể tải danh sách thực phẩm"))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    const delayDebounceFn = setTimeout(() => {
      loadData();
    }, 300);
    return () => clearTimeout(delayDebounceFn);
  }, [filters.q, filters.category, filters.menu_eligible, filters.missing_image, filters.has_quality_flags, page, pageSize]);

  async function updateFood(food, patch) {
    try {
      await adminPatch(`/foods/${food.food_id}`, patch);
      loadData();
    } catch (e) {
      alert("Lỗi cập nhật: " + e.message);
    }
  }

  const items = Array.isArray(data?.items) ? data.items : [];
  const totalItems = data?.total || 0;
  const totalPages = Math.ceil(totalItems / pageSize) || 1;

  return (
    <div className="space-y-5 animate-fadeIn">
      {/* Search inputs & Category Filters */}
      <div className="rounded-xl border border-[#E5E7EB] bg-white p-4 shadow-sm space-y-3">
        <div className="flex flex-col md:flex-row gap-3">
          <div className="relative md:flex-1">
            <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-slate-400 pointer-events-none">
              <svg className="h-[18px] w-[18px]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </span>
            <input
              type="text"
              value={filters.q}
              onChange={(e) => handleFilterChange("q", e.target.value)}
              placeholder="Nhập tên thực phẩm hoặc món ăn..."
              className="h-10 w-full pl-9 pr-4 rounded-xl border border-[#E5E7EB] bg-slate-50 text-sm outline-none focus:border-emerald-500 focus:bg-white transition"
            />
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <select
              className="h-10 rounded-xl border border-[#E5E7EB] bg-white px-3 text-sm font-bold text-slate-600 outline-none hover:bg-slate-50 transition cursor-pointer"
              value={filters.category}
              onChange={(e) => handleFilterChange("category", e.target.value)}
            >
              <option value="">Tất cả nhóm món</option>
              {categoryOptions.map((item) => (
                <option key={item} value={item}>{CATEGORY_MAP[item] || item}</option>
              ))}
            </select>

            <select
              className="h-10 rounded-xl border border-[#E5E7EB] bg-white px-3 text-sm font-bold text-slate-600 outline-none hover:bg-slate-50 transition cursor-pointer"
              value={filters.menu_eligible}
              onChange={(e) => handleFilterChange("menu_eligible", e.target.value)}
            >
              <option value="">Kiểm duyệt đề xuất</option>
              <option value="true">Được gợi ý</option>
              <option value="false">Không gợi ý</option>
            </select>
          </div>
        </div>

        {/* Quality flag checkbox filters */}
        <div className="flex flex-wrap items-center gap-5 pt-2 border-t border-slate-100 text-xs font-bold text-slate-400 tracking-wide uppercase">
          <label className="flex items-center gap-2 cursor-pointer hover:text-slate-600 transition">
            <input
              type="checkbox"
              checked={filters.missing_image}
              onChange={(e) => handleFilterChange("missing_image", e.target.checked)}
              className="h-4 w-4 text-emerald-600 rounded border-slate-300 focus:ring-emerald-500"
            />
            Chưa có hình ảnh
          </label>
          <label className="flex items-center gap-2 cursor-pointer hover:text-slate-600 transition">
            <input
              type="checkbox"
              checked={filters.has_quality_flags}
              onChange={(e) => handleFilterChange("has_quality_flags", e.target.checked)}
              className="h-4 w-4 text-emerald-600 rounded border-slate-300 focus:ring-emerald-500"
            />
            Có nhãn kiểm soát (Quality Flags)
          </label>
        </div>
      </div>

      {loading ? (
        <AdminLoadingState />
      ) : error ? (
        <AdminErrorState message={error} onRetry={loadData} />
      ) : items.length === 0 ? (
        <AdminEmptyState message="Không tìm thấy thực phẩm tương ứng" />
      ) : (
        <div className="space-y-4">
          <DataTable
            headers={[
              { label: "Món ăn & Thực phẩm" },
              { label: "Nhóm" },
              { label: "Dinh dưỡng / 100g" },
              { label: "Gợi ý", align: "center" },
              { label: "Ảnh", align: "center" },
              { label: "Thao tác", align: "right" }
            ]}
          >
            {items.map((food) => (
              <tr key={food?.food_id} className="hover:bg-slate-50/40 transition">
                <td className="px-4 py-2.5 font-bold text-slate-800">
                  <span className="text-sm">{food?.name}</span>
                  <span className="block text-xs text-slate-400 font-normal mt-0.5">ID: #{food?.food_id}</span>
                </td>
                <td className="px-4 py-2.5 align-middle text-sm text-slate-500 font-semibold">
                  {CATEGORY_MAP[food?.category] || food?.category}
                </td>
                <td className="px-4 py-2.5 align-middle text-sm text-slate-600">
                  {food?.calories} kcal · P {food?.protein}g · F {food?.fat}g · C {food?.carbs}g
                </td>
                <td className="px-4 py-2.5 text-center align-middle">
                  <StatusBadge type={food?.menu_eligible ? "success" : "danger"}>
                    {food?.menu_eligible ? "Có" : "Không"}
                  </StatusBadge>
                </td>
                <td className="px-4 py-2.5 text-center align-middle">
                  {food?.image_url ? (
                    <span className="text-emerald-600 font-bold text-xs">Có ảnh</span>
                  ) : (
                    <span className="text-rose-600 font-bold text-xs">Trống</span>
                  )}
                </td>
                <td className="px-4 py-2.5 align-middle text-right space-x-1 whitespace-nowrap">
                  <button
                    onClick={() => updateFood(food, { menu_eligible: !food.menu_eligible })}
                    className={`h-[30px] rounded-lg text-xs font-bold text-white px-2.5 transition ${
                      food?.menu_eligible ? "bg-rose-500 hover:bg-rose-600" : "bg-emerald-600 hover:bg-emerald-700"
                    }`}
                  >
                    {food?.menu_eligible ? "Khóa" : "Mở"}
                  </button>

                  <select
                    className="h-[30px] rounded-lg border border-slate-200 text-xs font-bold text-slate-600 bg-white px-1 cursor-pointer outline-none"
                    value={food?.category || "other"}
                    onChange={(e) => updateFood(food, { category: e.target.value, clean_category: e.target.value })}
                  >
                    {categoryOptions.map((item) => (
                      <option key={item} value={item}>{CATEGORY_MAP[item] || item}</option>
                    ))}
                  </select>
                </td>
              </tr>
            ))}
          </DataTable>

          {/* Dynamic Pagination Bar */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4 bg-white p-4 rounded-2xl border border-[#E5E7EB] shadow-sm text-xs font-bold text-slate-500">
            <div className="flex items-center gap-2">
              <span>Hiển thị</span>
              <select
                value={pageSize}
                onChange={(e) => {
                  setPageSize(Number(e.target.value));
                  setPage(1);
                }}
                className="h-8 rounded-lg border border-slate-200 bg-white px-2 outline-none cursor-pointer hover:bg-slate-50 transition"
              >
                <option value={25}>25</option>
                <option value={50}>50</option>
                <option value={100}>100</option>
              </select>
              <span>dòng trong tổng số {formatNumber(totalItems)} món ăn</span>
            </div>

            <div className="flex items-center gap-3">
              <button
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="h-8 px-3 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 disabled:opacity-40 disabled:hover:bg-white transition flex items-center justify-center gap-1 cursor-pointer"
              >
                ← Trang trước
              </button>
              <span className="text-slate-700">Trang {page} / {totalPages}</span>
              <button
                disabled={page >= totalPages}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                className="h-8 px-3 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 disabled:opacity-40 disabled:hover:bg-white transition flex items-center justify-center gap-1 cursor-pointer"
              >
                Trang sau →
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// D. NHÓM MÓN (FOOD CATEGORIES)
function CategoriesPage() {
  const [data, setData] = useState({ items: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadData = () => {
    setLoading(true);
    adminGet("/food-categories/summary")
      .then((d) => {
        setData(d || { items: [] });
        setError("");
      })
      .catch((e) => setError(e.message || "Không thể tải nhóm món"))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadData();
  }, []);

  if (loading) return <AdminLoadingState />;
  if (error) return <AdminErrorState message={error} onRetry={loadData} />;

  const items = Array.isArray(data?.items) ? data.items : [];
  if (!items.length) return <AdminEmptyState message="Chưa có dữ liệu nhóm món" />;

  const totalCount = items.reduce((acc, row) => acc + (row.count || 0), 0);

  return (
    <div className="space-y-5 animate-fadeIn">
      {/* Category grid analysis cards */}
      <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {items.map((item) => {
          const ratio = totalCount ? Math.round((item.count / totalCount) * 100) : 0;
          return (
            <div key={item.category} className="rounded-2xl border border-[#E5E7EB] bg-white p-5 flex flex-col justify-between group">
              <div className="space-y-0.5">
                <span className="text-xs font-bold text-slate-400">Nhóm thực phẩm</span>
                <h4 className="text-base font-black text-slate-800 tracking-tight group-hover:text-emerald-600 transition-colors">
                  {CATEGORY_MAP[item.category] || item.category}
                </h4>
              </div>

              <div className="mt-5 pt-3 border-t border-slate-100 flex items-end justify-between">
                <div className="space-y-1 w-1/2">
                  <div className="flex justify-between text-xs text-slate-400 font-bold">
                    <span>Tỷ lệ cơ sở</span>
                    <span>{ratio}%</span>
                  </div>
                  <div className="w-full bg-slate-100 rounded-full h-1">
                    <div className="bg-emerald-500 h-1 rounded-full" style={{ width: `${ratio}%` }} />
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-2xl font-black text-slate-900 leading-none">{formatNumber(item.count)}</div>
                  <p className="text-xs text-slate-400 mt-0.5">Món ăn</p>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// E. KIỂM TRA GỢI Ý (RECOMMENDATION TEST SANDBOX - RECOMMENDATION LAB)
function RecommendationTestPage() {
  const [form, setForm] = useState({
    gender: "male",
    age: 25,
    height_cm: 165,
    weight_kg: 45,
    target_weight_kg: 52,
    activity_level: "moderate",
    weight_gain_speed: "medium",
    diet_type: "balanced",
    budget_level: "standard",
    items_per_meal: 4,
    favorite_foods: "",
    disliked_foods: ""
  });
  const [result, setResult] = useState(null);
  const [running, setRunning] = useState(false);
  const [runError, setRunError] = useState("");

  const payload = useMemo(() => ({
    weight: Number(form.weight_kg),
    height: Number(form.height_cm),
    age: Number(form.age),
    sex: form.gender,
    activity: form.activity_level,
    weight_gain_speed: form.weight_gain_speed,
    gain_speed: form.weight_gain_speed,
    diet_type: form.diet_type,
    diet_style: form.diet_type,
    budget_level: form.budget_level,
    items_per_meal: Number(form.items_per_meal),
    target_weight: Number(form.target_weight_kg),
    favorite_foods: parseFoodList(form.favorite_foods),
    disliked_foods: parseFoodList(form.disliked_foods),
    save_user_data: false,
  }), [form]);

  async function runTest() {
    setRunning(true);
    setRunError("");
    setResult(null);
    try {
      const data = await adminPost("/recommendation-test", payload);
      setResult(data);
    } catch (e) {
      setRunError(e.message || "Thuật toán không tìm thấy lời giải tối ưu cho bộ ràng buộc dinh dưỡng này.");
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Sandbox Header Banner */}
      <div className="rounded-2xl border border-emerald-100 bg-emerald-50/50 p-4 px-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-sm">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
            <h2 className="text-sm font-bold text-slate-800">Môi trường thử nghiệm đề xuất — Recommendation Lab</h2>
          </div>
          <p className="text-xs text-slate-500 font-semibold leading-relaxed">
            Thiết lập hồ sơ giả lập để kiểm tra kết quả đề xuất. Trình giả định không làm ảnh hưởng đến dữ liệu thực tế.
          </p>
        </div>
        <span className="shrink-0 text-[10px] font-black uppercase tracking-wider text-emerald-700 bg-emerald-100/60 px-2.5 py-1 rounded-lg border border-emerald-200">
          Sandbox Mode
        </span>
      </div>

      <div className="grid gap-6 xl:grid-cols-12 items-start">
        {/* Simulation form on the left (42% width equivalent on 12-column grid) */}
        <div className="xl:col-span-5 rounded-2xl border border-[#E5E7EB] bg-white p-6 shadow-sm space-y-6">
          <div>
            <h3 className="text-sm font-bold text-slate-800 leading-none">Cấu hình hồ sơ mô phỏng</h3>
            <p className="text-xs text-slate-400 mt-1.5 font-semibold">Nhập thông số để kiểm tra khả năng tạo thực đơn.</p>
          </div>

          <div className="space-y-5">
            {/* A. Hồ sơ cơ bản */}
            <div className="space-y-3 pt-3 border-t border-slate-100">
              <div className="flex items-center gap-2">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                <h4 className="text-xs font-bold text-slate-800">Hồ sơ cơ bản</h4>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <label className="block">
                  <span className="text-xs font-bold text-slate-500 mb-1.5 block">Giới tính</span>
                  <select
                    className="h-11 w-full rounded-[14px] border border-slate-200 bg-slate-50/50 px-3.5 font-semibold text-slate-700 outline-none focus:border-emerald-500 focus:bg-white focus:ring-4 focus:ring-emerald-500/5 transition text-sm cursor-pointer"
                    value={form.gender}
                    onChange={(e) => setForm((prev) => ({ ...prev, gender: e.target.value }))}
                  >
                    <option value="male">Nam giới</option>
                    <option value="female">Nữ giới</option>
                  </select>
                </label>

                <label className="block">
                  <span className="text-xs font-bold text-slate-500 mb-1.5 block">Tuổi (Năm)</span>
                  <input
                    type="number"
                    className="h-11 w-full rounded-[14px] border border-slate-200 bg-slate-50/50 px-3.5 font-semibold text-slate-700 outline-none focus:border-emerald-500 focus:bg-white focus:ring-4 focus:ring-emerald-500/5 transition text-sm"
                    value={form.age}
                    onChange={(e) => setForm((prev) => ({ ...prev, age: e.target.value }))}
                  />
                </label>
              </div>
            </div>

            {/* B. Chỉ số cơ thể */}
            <div className="space-y-3 pt-3 border-t border-slate-100">
              <div className="flex items-center gap-2">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                <h4 className="text-xs font-bold text-slate-800">Chỉ số cơ thể</h4>
              </div>
              <div className="grid grid-cols-3 gap-3">
                <label className="block">
                  <span className="text-xs font-bold text-slate-500 mb-1.5 block">Chiều cao (cm)</span>
                  <input
                    type="number"
                    className="h-11 w-full rounded-[14px] border border-slate-200 bg-slate-50/50 px-3 font-semibold text-slate-700 outline-none focus:border-emerald-500 focus:bg-white focus:ring-4 focus:ring-emerald-500/5 transition text-sm"
                    value={form.height_cm}
                    onChange={(e) => setForm((prev) => ({ ...prev, height_cm: e.target.value }))}
                  />
                </label>
                <label className="block">
                  <span className="text-xs font-bold text-slate-500 mb-1.5 block">Cân nặng (kg)</span>
                  <input
                    type="number"
                    className="h-11 w-full rounded-[14px] border border-slate-200 bg-slate-50/50 px-3 font-semibold text-slate-700 outline-none focus:border-emerald-500 focus:bg-white focus:ring-4 focus:ring-emerald-500/5 transition text-sm"
                    value={form.weight_kg}
                    onChange={(e) => setForm((prev) => ({ ...prev, weight_kg: e.target.value }))}
                  />
                </label>
                <label className="block">
                  <span className="text-xs font-bold text-slate-500 mb-1.5 block">Mục tiêu (kg)</span>
                  <input
                    type="number"
                    className="h-11 w-full rounded-[14px] border border-slate-200 bg-slate-50/50 px-3 font-semibold text-slate-700 outline-none focus:border-emerald-500 focus:bg-white focus:ring-4 focus:ring-emerald-500/5 transition text-sm"
                    value={form.target_weight_kg}
                    onChange={(e) => setForm((prev) => ({ ...prev, target_weight_kg: e.target.value }))}
                  />
                </label>
              </div>
            </div>

            {/* C. Mục tiêu dinh dưỡng */}
            <div className="space-y-3 pt-3 border-t border-slate-100">
              <div className="flex items-center gap-2">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                <h4 className="text-xs font-bold text-slate-800">Mục tiêu dinh dưỡng</h4>
              </div>
              <label className="block">
                <span className="text-xs font-bold text-slate-500 mb-1.5 block">Mức độ hoạt động thể chất</span>
                <select
                  className="h-11 w-full rounded-[14px] border border-slate-200 bg-slate-50/50 px-3.5 font-semibold text-slate-700 outline-none focus:border-emerald-500 focus:bg-white focus:ring-4 focus:ring-emerald-500/5 transition text-sm cursor-pointer"
                  value={form.activity_level}
                  onChange={(e) => setForm((prev) => ({ ...prev, activity_level: e.target.value }))}
                >
                  <option value="sedentary">Ít hoạt động (Dân văn phòng)</option>
                  <option value="lightly_active">Nhẹ nhàng (Thể thao 1-2 ngày/tuần)</option>
                  <option value="moderate">Vừa phải (Thể thao 3-5 ngày/tuần)</option>
                  <option value="very_active">Hoạt động mạnh (Vận động viên)</option>
                </select>
              </label>

              <div className="grid grid-cols-2 gap-4">
                <label className="block">
                  <span className="text-xs font-bold text-slate-500 mb-1.5 block">Tốc độ tăng cân</span>
                  <select
                    className="h-11 w-full rounded-[14px] border border-slate-200 bg-slate-50/50 px-3.5 font-semibold text-slate-700 outline-none focus:border-emerald-500 focus:bg-white focus:ring-4 focus:ring-emerald-500/5 transition text-sm cursor-pointer"
                    value={form.weight_gain_speed}
                    onChange={(e) => setForm((prev) => ({ ...prev, weight_gain_speed: e.target.value }))}
                  >
                    <option value="slow">Chậm rãi (0.25 kg / tuần)</option>
                    <option value="medium">Bình thường (0.5 kg / tuần)</option>
                    <option value="fast">Nhanh (0.75 kg / tuần)</option>
                  </select>
                </label>

                <label className="block">
                  <span className="text-xs font-bold text-slate-500 mb-1.5 block">Số món mỗi bữa</span>
                  <input
                    type="number"
                    className="h-11 w-full rounded-[14px] border border-slate-200 bg-slate-50/50 px-3.5 font-semibold text-slate-700 outline-none focus:border-emerald-500 focus:bg-white focus:ring-4 focus:ring-emerald-500/5 transition text-sm"
                    value={form.items_per_meal}
                    onChange={(e) => setForm((prev) => ({ ...prev, items_per_meal: e.target.value }))}
                  />
                </label>
              </div>
            </div>

            {/* D. Tùy chọn ăn uống */}
            <div className="space-y-3 pt-3 border-t border-slate-100">
              <div className="flex items-center gap-2">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                <h4 className="text-xs font-bold text-slate-800">Tùy chọn ăn uống</h4>
              </div>
              <label className="block">
                <span className="text-xs font-bold text-slate-500 mb-1.5 block">Chế độ dinh dưỡng (Diet Profile)</span>
                <select
                  className="h-11 w-full rounded-[14px] border border-slate-200 bg-slate-50/50 px-3.5 font-semibold text-slate-700 outline-none focus:border-emerald-500 focus:bg-white focus:ring-4 focus:ring-emerald-500/5 transition text-sm cursor-pointer"
                  value={form.diet_type}
                  onChange={(e) => setForm((prev) => ({ ...prev, diet_type: e.target.value }))}
                >
                  <option value="balanced">Cân bằng tối ưu (Carb/Protein/Fat)</option>
                  <option value="high_protein">Nhiều đạm (High Protein)</option>
                  <option value="vegetarian">Chay thanh đạm</option>
                </select>
              </label>

              <label className="block">
                <span className="text-xs font-bold text-slate-500 mb-1.5 block">Món ăn loại trừ</span>
                <input
                  type="text"
                  placeholder="Ví dụ: gà, tôm, nước béo..."
                  className="h-11 w-full rounded-[14px] border border-slate-200 bg-slate-50/50 px-3.5 font-semibold text-slate-700 outline-none focus:border-emerald-500 focus:bg-white focus:ring-4 focus:ring-emerald-500/5 transition text-sm"
                  value={form.disliked_foods}
                  onChange={(e) => setForm((prev) => ({ ...prev, disliked_foods: e.target.value }))}
                />
              </label>
            </div>
          </div>

          <button
            disabled={running}
            onClick={runTest}
            className="h-12 w-full rounded-2xl bg-emerald-600 hover:bg-emerald-700 active:bg-emerald-800 font-bold text-white transition disabled:opacity-60 text-sm shadow-md shadow-emerald-50 flex items-center justify-center gap-2 cursor-pointer"
          >
            {running ? (
              <>
                <svg className="animate-spin h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                <span>Đang chạy thuật toán...</span>
              </>
            ) : (
              "Chạy kiểm tra gợi ý"
            )}
          </button>
        </div>

        {/* Output results dashboard on the right (58% width equivalent on 12-column grid) */}
        <div className="xl:col-span-7 rounded-2xl border border-[#E5E7EB] bg-white p-6 shadow-sm min-h-[580px] flex flex-col justify-between">
          {running ? (
            <div className="flex-1 flex flex-col items-center justify-center py-20 text-center space-y-4">
              <svg className="animate-spin h-10 w-10 text-emerald-600" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              <div className="space-y-1">
                <h4 className="text-sm font-bold text-slate-800">Đang chạy thuật toán...</h4>
                <p className="text-xs text-slate-400 font-semibold leading-relaxed">
                  Trình tối ưu dinh dưỡng đang liên kết dữ liệu và phân tích chỉ số kcal.
                </p>
              </div>
            </div>
          ) : runError ? (
            <div className="flex-1 flex flex-col items-center justify-center py-12 text-center space-y-4">
              <div className="h-12 w-12 rounded-full bg-rose-50 border border-rose-100 text-rose-500 flex items-center justify-center">
                <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              </div>
              <div className="space-y-1.5 max-w-md">
                <h4 className="text-sm font-bold text-slate-800">Không thể tạo gợi ý</h4>
                <p className="text-xs text-rose-600 bg-rose-50/50 p-3 rounded-xl border border-rose-100 font-bold leading-relaxed">{runError}</p>
              </div>
              <button
                onClick={runTest}
                className="px-4 py-2 bg-slate-100 hover:bg-slate-200 active:bg-slate-300 text-slate-700 font-bold text-xs rounded-xl transition cursor-pointer"
              >
                Chạy lại
              </button>
            </div>
          ) : result ? (
            <div className="space-y-6 animate-fadeIn flex-1 flex flex-col justify-between">
              <div className="space-y-6">
                <div>
                  <h3 className="text-sm font-bold text-slate-800 leading-none">Kết quả mô phỏng</h3>
                  <p className="text-xs text-slate-400 mt-1.5 font-semibold">Báo cáo chỉ số calo tối ưu và chất lượng thực đơn đề xuất</p>
                </div>

                {/* KPI Summary Rows */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                  <div className="p-4 bg-slate-50/60 rounded-xl border border-slate-100/80 font-bold">
                    <span className="text-[10px] text-slate-400 uppercase tracking-wider block">BMI</span>
                    <p className="text-xl font-black text-slate-800 mt-1">{result.bmi || result.profile_summary?.bmi || 0}</p>
                    <span className="text-[10px] text-emerald-600 font-black mt-1 block">
                      {result.bmi_label || result.profile_summary?.bmi_label || "Bình thường"}
                    </span>
                  </div>

                  <div className="p-4 bg-slate-50/60 rounded-xl border border-slate-100/80 font-bold">
                    <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Mục tiêu kcal</span>
                    <p className="text-xl font-black text-slate-800 mt-1">{Math.round(result.target_kcal || result.nutrition_target?.calorie_target || 0)}</p>
                    <span className="text-[10px] text-slate-400 mt-1 block font-semibold">Khuyến nghị</span>
                  </div>

                  <div className="p-4 bg-slate-50/60 rounded-xl border border-slate-100/80 font-bold">
                    <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Calo thực tế</span>
                    <p className="text-xl font-black text-slate-800 mt-1">{Math.round(result.meal_plan?.total_kcal || 0)}</p>
                    <span className="text-[10px] text-orange-500 font-black mt-1 block">
                      Lệch: {Math.round(result.kcal_delta || result.validation?.kcalDiff || 0)} kcal
                    </span>
                  </div>

                  <div className="p-4 bg-slate-50/60 rounded-xl border border-slate-100/80 font-bold">
                    <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Trạng thái kết quả</span>
                    <p className="text-xl font-black text-slate-800 mt-1">
                      {result.validation?.is_valid || result.validation?.isValid ? "Hợp lệ" : "Cần tinh chỉnh"}
                    </p>
                    <span className="text-[10px] text-emerald-600 font-black mt-1 block">Tối ưu hóa</span>
                  </div>
                </div>

                {/* Validation Status Block */}
                <div className="space-y-3">
                  {result.validation?.is_valid || result.validation?.isValid ? (
                    <div className="bg-emerald-50/60 p-4 rounded-xl border border-emerald-100/80 text-xs text-emerald-800 leading-relaxed font-bold flex items-start gap-2.5">
                      <span className="h-5 w-5 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center text-xs font-black shrink-0">✓</span>
                      <div className="space-y-0.5">
                        <p className="font-extrabold text-emerald-900">Kết quả hợp lệ</p>
                        <p className="font-semibold text-emerald-700/90">Thuật toán đề xuất đã hội tụ và đáp ứng hoàn hảo các ràng buộc về kcal và tỷ lệ nhóm chất dinh dưỡng.</p>
                      </div>
                    </div>
                  ) : (
                    <div className="bg-amber-50/60 p-4 rounded-xl border border-amber-100/80 text-xs text-amber-800 leading-relaxed font-bold flex items-start gap-2.5">
                      <span className="h-5 w-5 rounded-full bg-amber-100 text-amber-700 flex items-center justify-center text-xs font-black shrink-0">!</span>
                      <div className="space-y-0.5">
                        <p className="font-extrabold text-amber-900">Cần tinh chỉnh</p>
                        <p className="font-semibold text-amber-700/90">Đề xuất được tạo ra sau các vòng lặp điều chỉnh, tuy nhiên tỷ lệ macronutrient hoặc kcal chưa đạt mức hội tụ cao nhất.</p>
                      </div>
                    </div>
                  )}

                  {Array.isArray(result.validation?.warnings) && result.validation.warnings.length > 0 && (
                    <div className="bg-slate-50 p-4 rounded-xl border border-slate-100 text-xs text-slate-600 leading-relaxed font-bold">
                      <p className="font-bold text-slate-700 mb-2">Chi tiết cảnh báo thuật toán ({result.validation.warnings.length}):</p>
                      <ul className="list-disc pl-4 space-y-1 text-slate-500">
                        {result.validation.warnings.map((w, index) => (
                          <li key={index} className="font-semibold">{w}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>

                {/* Meal Preview Structure */}
                <div className="space-y-3 pt-2">
                  <h4 className="text-xs font-bold text-slate-800 flex items-center gap-2">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                    Cơ cấu thực đơn đề xuất
                  </h4>
                  <div className="grid gap-4 sm:grid-cols-3">
                    {((result.meal_plan?.meals || result.fixed_menu || [])).map((mealGroup, mIndex) => {
                      const mealNameMap = {
                        breakfast: "Bữa sáng",
                        lunch: "Bữa trưa",
                        dinner: "Bữa tối",
                        snack: "Bữa phụ",
                        "Bữa sáng": "Bữa sáng",
                        "Bữa trưa": "Bữa trưa",
                        "Bữa tối": "Bữa tối",
                        "Bữa phụ": "Bữa phụ"
                      };
                      const mType = mealGroup.meal_type || mealGroup.meal || "";
                      const displayName = mealNameMap[mType] || (mType.charAt(0).toUpperCase() + mType.slice(1));
                      const mKcal = mealGroup.total_kcal || mealGroup.items?.reduce((sum, item) => sum + (item.kcal || item.calories || 0), 0) || 0;
                      const mItems = mealGroup.items || [];
                      return (
                        <div key={mIndex} className="rounded-xl border border-slate-100 bg-slate-50/50 p-4 flex flex-col justify-between space-y-3 shadow-inner">
                          <div className="flex justify-between items-center pb-2 border-b border-slate-200/60 shrink-0">
                            <span className="text-xs font-black text-slate-800">{displayName}</span>
                            <span className="text-[10px] font-black text-emerald-600 bg-emerald-50 border border-emerald-100 px-1.5 py-0.5 rounded-md">
                              {Math.round(mKcal)} kcal
                            </span>
                          </div>
                          <ul className="space-y-2 flex-1 overflow-y-auto max-h-[160px] pr-1">
                            {mItems.map((item, iIndex) => (
                              <li key={iIndex} className="text-[11px] leading-relaxed">
                                <span className="font-bold text-slate-700 block">{item.name || item.new_item || item.reason}</span>
                                <span className="block text-[9px] text-slate-400 font-semibold mt-0.5">
                                  {item.portion_display || item.serving_display || `${Math.round(item.quantity_g || 100)}g`} · {Math.round(item.kcal || item.calories || 0)} kcal
                                </span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>

              {/* Collapsible raw data container */}
              <details className="bg-slate-50 p-3.5 rounded-xl border border-slate-100 text-xs">
                <summary className="cursor-pointer font-bold text-slate-500 select-none hover:text-slate-800 transition">Xem dữ liệu kỹ thuật</summary>
                <pre className="max-h-[200px] overflow-auto rounded-xl bg-slate-950 p-3.5 text-xs font-mono text-emerald-400 mt-3 leading-relaxed border border-slate-800">
                  {JSON.stringify(result, null, 2)}
                </pre>
              </details>
            </div>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center py-10 text-center space-y-5">
              <div className="h-16 w-16 bg-slate-50 rounded-full border border-slate-100 flex items-center justify-center text-slate-400">
                <svg className="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                </svg>
              </div>
              <div className="space-y-1.5 max-w-xs">
                <h4 className="text-sm font-bold text-slate-800">Chưa có kết quả kiểm tra</h4>
                <p className="text-xs text-slate-400 font-semibold leading-relaxed">
                  Nhập thông số bên trái rồi nhấn Chạy kiểm tra gợi ý.
                </p>
              </div>

              <div className="w-full max-w-[280px] bg-slate-50/60 border border-slate-100 rounded-xl p-4 text-left space-y-3 font-bold text-slate-500 text-[11px] shrink-0 mt-2 shadow-inner">
                <div className="flex items-center gap-2.5">
                  <span className="h-5 w-5 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center text-xs font-black shrink-0">✓</span>
                  <span>Tính nhu cầu kcal</span>
                </div>
                <div className="flex items-center gap-2.5">
                  <span className="h-5 w-5 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center text-xs font-black shrink-0">✓</span>
                  <span>Kiểm tra ràng buộc món ăn</span>
                </div>
                <div className="flex items-center gap-2.5">
                  <span className="h-5 w-5 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center text-xs font-black shrink-0">✓</span>
                  <span>Đánh giá cấu trúc thực đơn</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// F. THỰC ĐƠN ĐÃ TẠO (MEAL PLANS LOGS)
function MealPlansPage() {
  const [filters, setFilters] = useState({ q: "", status: "", only_errors: false });
  const [data, setData] = useState({ items: [] });
  const [selectedJson, setSelectedJson] = useState(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadData = () => {
    setLoading(true);
    adminGet("/meal-plans", filters)
      .then((d) => {
        setData(d || { items: [] });
        setError("");
      })
      .catch((e) => setError(e.message || "Không thể tải danh sách thực đơn"))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    const delayDebounceFn = setTimeout(() => {
      loadData();
    }, 300);
    return () => clearTimeout(delayDebounceFn);
  }, [filters.q, filters.status, filters.only_errors]);

  const items = Array.isArray(data?.items) ? data.items : [];

  return (
    <div className="space-y-5 animate-fadeIn">
      {/* Filters search */}
      <FilterBar>
        <div className="relative w-full md:flex-1">
          <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-slate-400 pointer-events-none">
            <svg className="h-[18px] w-[18px]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </span>
          <input
            type="text"
            value={filters.q}
            onChange={(e) => setFilters((prev) => ({ ...prev, q: e.target.value }))}
            placeholder="Tìm theo email người dùng..."
            className="h-10 w-full pl-9 pr-4 rounded-xl border border-[#E5E7EB] bg-slate-50 text-sm outline-none focus:border-emerald-500 focus:bg-white transition"
          />
        </div>

        <div className="flex w-full md:w-auto items-center justify-end gap-3 shrink-0 flex-wrap sm:flex-nowrap">
          <input
            type="text"
            value={filters.status}
            onChange={(e) => setFilters((prev) => ({ ...prev, status: e.target.value }))}
            placeholder="Trạng thái"
            className="h-10 w-28 rounded-xl border border-[#E5E7EB] bg-white px-3 text-sm font-bold text-slate-600 outline-none hover:bg-slate-50 focus:bg-white transition"
          />

          <label className="flex items-center gap-2 cursor-pointer text-xs font-bold text-slate-400 tracking-wide uppercase">
            <input
              type="checkbox"
              checked={filters.only_errors}
              onChange={(e) => setFilters((prev) => ({ ...prev, only_errors: e.target.checked }))}
              className="h-4 w-4 text-emerald-600 rounded border-slate-300 focus:ring-emerald-500"
            />
            Chỉ thực đơn lỗi
          </label>
        </div>
      </FilterBar>

      {loading ? (
        <AdminLoadingState />
      ) : error ? (
        <AdminErrorState message={error} onRetry={loadData} />
      ) : items.length === 0 ? (
        <AdminEmptyState message="Không tìm thấy thực đơn nào" />
      ) : (
        <DataTable
          headers={[
            { label: "Email người dùng" },
            { label: "Năng lượng thực tế / Mục tiêu kcal" },
            { label: "Trạng thái" },
            { label: "Ngày khởi tạo" },
            { label: "Thao tác", align: "right" }
          ]}
        >
          {items.map((row) => (
            <tr key={row?.id} className="hover:bg-slate-50/40 transition">
              <td className="px-4 py-2.5">
                <div className="font-bold text-slate-800 text-sm">{row?.user_email}</div>
                <div className="text-[11px] text-slate-400 mt-0.5">ID: #{row?.id} · Ngày thực đơn: {row?.plan_date}</div>
              </td>
              <td className="px-4 py-2.5 font-bold text-slate-700 align-middle">
                {row?.total_kcal} / {row?.target_kcal} kcal
              </td>
              <td className="px-4 py-2.5 align-middle">
                <StatusBadge type={row?.status === "active" || row?.status === "ACTIVE" ? "success" : "neutral"}>
                  {row?.status || "Không hoạt động"}
                </StatusBadge>
              </td>
              <td className="px-4 py-2.5 align-middle text-slate-400 font-bold text-xs">
                {row?.created_at?.slice(0, 10)}
              </td>
              <td className="px-4 py-2.5 align-middle text-right">
                <button
                  onClick={() => {
                    adminGet(`/meal-plans/${row.id}`).then((res) => {
                      setSelectedJson(res);
                      setIsDrawerOpen(true);
                    });
                  }}
                  className="h-[30px] rounded-lg bg-slate-50 hover:bg-slate-100 text-xs font-bold text-slate-600 px-3 border border-slate-200 transition"
                >
                  Xem chi tiết
                </button>
              </td>
            </tr>
          ))}
        </DataTable>
      )}

      {/* Slide Drawer for detailed JSON response view */}
      <DetailDrawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        title="Dữ liệu chi tiết thực đơn"
        subtitle={`ID bản ghi lưu trữ: #${selectedJson?.id}`}
      >
        {selectedJson && (
          <div className="space-y-4">
            <div className="space-y-1.5">
              <span className="text-xs font-bold text-slate-400 block">Dữ liệu chi tiết</span>
              <pre className="max-h-[500px] overflow-auto rounded-xl bg-slate-900 p-4 text-[11px] font-mono text-emerald-400 leading-relaxed shadow-inner">
                {JSON.stringify(selectedJson, null, 2)}
              </pre>
            </div>
          </div>
        )}
      </DetailDrawer>
    </div>
  );
}

// G. LỖI HỆ THỐNG (SYSTEM ERRORS QUEUE)
function ErrorsPage() {
  const [data, setData] = useState({ items: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadData = () => {
    setLoading(true);
    adminGet("/system-errors")
      .then((d) => {
        setData(d || { items: [] });
        setError("");
      })
      .catch((e) => setError(e.message || "Không thể tải nhật ký lỗi hệ thống"))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadData();
  }, []);

  async function resolveError(errorId) {
    try {
      await adminPatch(`/system-errors/${errorId}/resolve`, {});
      loadData();
    } catch (e) {
      alert("Lỗi khi xử lý: " + e.message);
    }
  }

  if (loading) return <AdminLoadingState />;
  if (error) return <AdminErrorState message={error} onRetry={loadData} />;

  const items = Array.isArray(data?.items) ? data.items : [];
  if (!items.length) {
    return (
      <div className="animate-fadeIn">
        <AdminEmptyState
          message="Không có lỗi hệ thống ghi nhận"
          desc="Hệ thống đang hoạt động an toàn và ổn định tuyệt đối."
          icon={
            <svg className="h-7 w-7 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04" />
            </svg>
          }
        />
      </div>
    );
  }

  return (
    <div className="space-y-4 animate-fadeIn">
      <DataTable
        headers={[
          { label: "Thời gian" },
          { label: "API Endpoint" },
          { label: "Phân loại & Nội dung lỗi" },
          { label: "Tình trạng", align: "center" },
          { label: "Xử lý", align: "right" }
        ]}
      >
        {items.map((row) => (
          <tr key={row?.id} className="hover:bg-slate-50/40 transition">
            <td className="px-4 py-3 text-slate-500 font-bold text-xs align-middle">
              {row?.time?.replace("T", " ").slice(11, 19)}
            </td>
            <td className="px-4 py-3 font-mono text-xs text-slate-500 align-middle font-bold">
              {row?.endpoint}
            </td>
            <td className="px-4 py-3 max-w-xs">
              <div className="text-xs bg-rose-50 border border-rose-100 rounded-xl p-3 text-rose-700 leading-normal">
                <strong className="block mb-1 text-xs uppercase tracking-wide">{row?.error_type}</strong>
                {row?.message}
              </div>
            </td>
            <td className="px-4 py-3 text-center align-middle">
              <StatusBadge type={row?.status === "resolved" ? "success" : "danger"}>
                {row?.status || "unresolved"}
              </StatusBadge>
            </td>
            <td className="px-4 py-3 align-middle text-right">
              {row?.status !== "resolved" ? (
                <button
                  onClick={() => resolveError(row.id)}
                  className="h-[30px] rounded-lg bg-emerald-600 hover:bg-emerald-700 text-xs font-bold text-white px-3 transition shadow-sm"
                >
                  Xác nhận xử lý
                </button>
              ) : (
                <span className="text-xs font-bold text-slate-400 italic">Đã xử lý xong</span>
              )}
            </td>
          </tr>
        ))}
      </DataTable>
    </div>
  );
}

// H. ADMIN NOT FOUND PAGE
function AdminNotFound({ onGoHome }) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[360px] bg-white border border-[#E5E7EB] rounded-2xl p-8 text-center shadow-sm">
      <div className="h-12 w-12 bg-slate-50 border border-slate-100 rounded-full flex items-center justify-center mb-3">
        <svg className="h-5 w-5 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      </div>
      <h3 className="text-sm font-bold text-slate-800">Đường dẫn không hợp lệ</h3>
      <p className="text-xs text-slate-400 mt-1 max-w-xs">Vui lòng quay lại màn hình điều phối chính.</p>
      <button
        onClick={onGoHome}
        className="mt-5 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-xl text-xs transition duration-150"
      >
        Quay lại màn hình chính
      </button>
    </div>
  );
}


// ============================================================================
// 4. MAIN ADMINVIEW SHELL CONTAINER
// ============================================================================
export default function AdminView(props) {
  return (
    <ErrorBoundary>
      <AdminShell {...props} />
    </ErrorBoundary>
  );
}

function AdminShell({ user, onLogout }) {
  const getSectionFromPath = () => {
    const raw = window.location.pathname.split("/")[2] || "overview";
    return navItems.some(([key]) => key === raw) ? raw : "overview";
  };

  const [section, setSection] = useState(getSectionFromPath);
  const [statsRefreshed, setStatsRefreshed] = useState(0);

  const currentNav = useMemo(() => {
    return navItems.find(([key]) => key === section) || navItems[0];
  }, [section]);

  function navigate(key) {
    const safeKey = navItems.some(([itemKey]) => itemKey === key) ? key : "overview";
    setSection(safeKey);
    window.history.pushState({}, "", `/admin/${safeKey}`);
  }

  useEffect(() => {
    const sync = () => setSection(getSectionFromPath());
    window.addEventListener("popstate", sync);
    return () => window.removeEventListener("popstate", sync);
  }, []);

  const PageComponent = useMemo(() => {
    const pageMap = {
      overview: () => (
        <OverviewPage
          onNavigate={navigate}
          statsRefreshed={statsRefreshed}
          onRefreshStats={() => setStatsRefreshed((p) => p + 1)}
        />
      ),
      users: UsersPage,
      foods: FoodsPage,
      "food-categories": CategoriesPage,
      "recommendation-test": RecommendationTestPage,
      "meal-plans": MealPlansPage,
      "system-errors": ErrorsPage,
    };
    return pageMap[section] || pageMap.overview;
  }, [section, statsRefreshed]);

  return (
    <div className="min-h-screen bg-[#F8FAFC] text-slate-900 flex font-sans leading-relaxed">
      
      {/* 1. SIDEBAR (Sleek Modern White Style - reduced to 260px width) */}
      <aside className="fixed inset-y-0 left-0 hidden w-[260px] flex-col bg-white border-r border-[#E5E7EB] lg:flex z-30 shadow-sm animate-fadeIn">
        {/* Brand Logo Banner */}
        <div className="flex h-[72px] items-center gap-3 px-6 shrink-0 border-b border-slate-50">
          <div className="h-9 w-9 rounded-xl bg-gradient-to-tr from-emerald-500 to-teal-600 flex items-center justify-center text-white text-base font-black shadow-sm">
            N
          </div>
          <div className="min-w-0">
            <div className="text-sm font-black text-slate-900 tracking-tight leading-none">NutriGain</div>
            <div className="text-[10px] font-bold text-emerald-600 mt-1.5 uppercase">Admin Console</div>
          </div>
        </div>

        {/* Group Navigation links */}
        <div className="flex-1 overflow-y-auto py-5 space-y-6 sidebar-scroll">
          
          {/* Section: CORE */}
          <div className="space-y-1.5 px-3">
            <span className="text-xs font-bold text-slate-400 px-3 block">Tổng quan</span>
            <nav className="space-y-0.5">
              {navItems.slice(0, 1).map(([key, label]) => {
                const isActive = section === key;
                return (
                  <button
                    key={key}
                    onClick={() => navigate(key)}
                    className={`flex w-full items-center gap-3 py-2.5 px-3 text-sm font-bold transition-all rounded-xl duration-150 ${
                      isActive
                        ? "bg-emerald-50 text-emerald-700 font-extrabold"
                        : "text-slate-500 hover:bg-slate-50 hover:text-slate-900"
                    }`}
                  >
                    <span className="shrink-0">{NAV_ICONS[key]}</span>
                    {label}
                  </button>
                );
              })}
            </nav>
          </div>

          {/* Section: DATABASE */}
          <div className="space-y-1.5 px-3">
            <span className="text-xs font-bold text-slate-400 px-3 block">Quản lý</span>
            <nav className="space-y-0.5">
              {navItems.slice(1, 4).concat(navItems.slice(5, 6)).map(([key, label]) => {
                const isActive = section === key;
                return (
                  <button
                    key={key}
                    onClick={() => navigate(key)}
                    className={`flex w-full items-center gap-3 py-2.5 px-3 text-sm font-bold transition-all rounded-xl duration-150 ${
                      isActive
                        ? "bg-emerald-50 text-emerald-700 font-extrabold"
                        : "text-slate-500 hover:bg-slate-50 hover:text-slate-900"
                    }`}
                  >
                    <span className="shrink-0">{NAV_ICONS[key]}</span>
                    {label}
                  </button>
                );
              })}
            </nav>
          </div>

          {/* Section: SYSTEMS */}
          <div className="space-y-1.5 px-3">
            <span className="text-xs font-bold text-slate-400 px-3 block">Công cụ</span>
            <nav className="space-y-0.5">
              {navItems.slice(4, 5).concat(navItems.slice(6)).map(([key, label]) => {
                const isActive = section === key;
                return (
                  <button
                    key={key}
                    onClick={() => navigate(key)}
                    className={`flex w-full items-center gap-3 py-2.5 px-3 text-sm font-bold transition-all rounded-xl duration-150 ${
                      isActive
                        ? "bg-emerald-50 text-emerald-700 font-extrabold"
                        : "text-slate-500 hover:bg-slate-50 hover:text-slate-900"
                    }`}
                  >
                    <span className="shrink-0">{NAV_ICONS[key]}</span>
                    {label}
                  </button>
                );
              })}
            </nav>
          </div>
        </div>

        {/* Sidebar Footer User detail & Logout */}
        <div className="border-t border-slate-100 p-4 shrink-0 bg-slate-50/50">
          <div className="mb-2.5 rounded-xl bg-white p-2.5 flex items-center gap-2 border border-[#E5E7EB] shadow-inner">
            <div className="h-7 w-7 rounded-full bg-emerald-50 text-emerald-700 flex items-center justify-center font-black text-xs shrink-0 border border-emerald-100">
              A
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-xs font-bold text-slate-700 leading-none">{user?.email || "admin@nutrigain.com"}</p>
              <p className="text-[10px] font-bold text-emerald-600 mt-1 leading-none">{user?.role || "ADMIN"}</p>
            </div>
          </div>
          <button
            onClick={onLogout}
            className="flex w-full items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-xs font-bold text-slate-600 hover:text-rose-600 hover:bg-rose-50 transition-all duration-150 cursor-pointer"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
              <path strokeLinecap="round" strokeLinejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
            Đăng xuất
          </button>
        </div>
      </aside>

      {/* 2. MAIN WORKSPACE (increased width space by adapting to pl-[260px]) */}
      <main className="lg:pl-[260px] flex-1 flex flex-col min-w-0">
        {/* Top Header sticky with prominent text scaling */}
        <header className="sticky top-0 z-20 flex h-[80px] items-center justify-between border-b border-[#E5E7EB] bg-white/95 px-6 md:px-8 backdrop-blur shadow-sm">
          <div className="min-w-0 space-y-1">
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight leading-none">
              {currentNav ? currentNav[1] : "Hộp Điều Hành"}
            </h1>
            <p className="text-sm text-slate-500 leading-none">
              {SUBTITLE_MAP[section] || "Giám sát sức khỏe người dùng và đề xuất dinh dưỡng NutriGain."}
            </p>
          </div>

          {/* Mobile responsive navigation toggles */}
          <div className="flex gap-1 overflow-x-auto lg:hidden py-1 max-w-[140px] sm:max-w-xs md:max-w-md shrink-0">
            {navItems.map(([key, label]) => {
              const isActive = section === key;
              return (
                <button
                  key={key}
                  onClick={() => navigate(key)}
                  className={`shrink-0 rounded-xl px-2.5 py-1 text-xs font-bold transition-all ${
                    isActive ? "bg-emerald-600 text-white shadow-sm" : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                  }`}
                >
                  {label}
                </button>
              );
            })}
          </div>
        </header>

        {/* Main Workspace Body container */}
        <section className="p-6 md:p-8 flex-1 max-w-[1400px] w-full mx-auto">
          {PageComponent ? (
            <div key={section}>
              <PageComponent />
            </div>
          ) : (
            <AdminNotFound onGoHome={() => navigate("overview")} />
          )}
        </section>
      </main>
    </div>
  );
}

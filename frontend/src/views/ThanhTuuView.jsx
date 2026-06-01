import GentleMotivationPanel from "../components/gamification/GentleMotivationPanel";
import { PageHeader } from "../components/PageHeader";

export default function ThanhTuuView({ onNavigate, gamificationRefreshKey }) {
  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="THÀNH TÍCH"
        title="Thành tích"
        subtitle="Theo dõi chuỗi duy trì, ghi nhận nhỏ và thử thách hôm nay."
      />

      <div className="opacity-95">
        <GentleMotivationPanel onAction={() => onNavigate?.("journal")} refreshKey={gamificationRefreshKey} />
      </div>

      {/* CTA to continue today's journey */}
      <section className="rounded-[24px] bg-gradient-to-br from-emerald-50 to-white p-6 shadow-sm ring-1 ring-emerald-100">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h3 className="text-xl font-black text-slate-900">Tiếp tục hành trình hôm nay</h3>
            <p className="mt-1 text-sm font-semibold text-slate-600">Quay lại tổng quan để xem bước tiếp theo của bạn.</p>
          </div>
          <button
            type="button"
            onClick={() => onNavigate?.("overview")}
            className="flex h-11 items-center justify-center rounded-2xl bg-emerald-600 px-5 text-sm font-black text-white shadow-md hover:bg-emerald-700 shrink-0"
          >
            Về tổng quan
          </button>
        </div>
      </section>
    </div>
  );
}

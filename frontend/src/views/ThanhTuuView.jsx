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
    </div>
  );
}

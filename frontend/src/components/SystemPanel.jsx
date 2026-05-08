export default function SystemPanel({ progress, bmr, tdee }) {
  return (
    <section className="glass-panel p-5">
      <div>
        <p className="text-xs font900 uppercase tracking-[0.18em] text-brand-primary">
          Hệ thống
        </p>
        <h2 className="mt-2 text-xl font-black text-brand-text-main">Trạng thái & nhắc nhở</h2>
      </div>

      <div className="mt-5 rounded-3xl bg-brand-navy p-5 text-white">
        <div className="flex items-center justify-between text-sm font900">
          <span>Tiến độ mục tiêu calories</span>
          <span>{progress}%</span>
        </div>
        <div className="mt-3 h-3 overflow-hidden rounded-full bg-white/15">
          <div
            className="h-full rounded-full bg-gradient-to-r from-brand-orange to-brand-primary"
            style={{ width: `${Math.min(progress, 100)}%` }}
          />
        </div>
        <p className="mt-3 text-sm font700 leading-6 text-white/75">
          Bạn đã chạm mốc calories hôm nay. Ưu tiên bữa nhẹ giàu protein nếu còn đói.
        </p>
      </div>

      <div className="mt-4 space-y-3">
        <StatusRow label="API dinh dưỡng" value="Online" tone="green" />
        <StatusRow label="Đồng bộ lịch sử" value="5 phút trước" tone="blue" />
        <StatusRow label="BMR / TDEE" value={`${bmr} / ${tdee}`} tone="orange" />
      </div>
    </section>
  );
}

function StatusRow({ label, value, tone }) {
  const dotClass = {
    green: "bg-brand-primary",
    blue: "bg-sky-500",
    orange: "bg-brand-orange",
  }[tone];

  return (
    <div className="flex items-center justify-between rounded-2xl bg-white/80 px-4 py-3 ring-1 ring-brand-border">
      <div className="flex items-center gap-3">
        <span className={`h-2.5 w-2.5 rounded-full ${dotClass}`} />
        <span className="text-sm font800 text-brand-text-sub">{label}</span>
      </div>
      <strong className="text-sm font900 text-brand-text-main">{value}</strong>
    </div>
  );
}

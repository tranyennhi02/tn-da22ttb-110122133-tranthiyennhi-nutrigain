import MealCard from "./MealCard";

export default function MealSection({ meals, favoriteMeals, ratings, onFavorite, onRate }) {
  const totalMeals = meals.reduce((sum, meal) => sum + meal.items.length, 0);

  return (
    <section className="space-y-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font900 uppercase tracking-[0.18em] text-brand-primary">
            Nhật ký ăn uống
          </p>
          <h2 className="mt-2 text-2xl font-black text-brand-text-main">Bữa ăn hôm nay</h2>
        </div>
        <div className="rounded-2xl bg-brand-surface px-4 py-3 text-sm font900 text-brand-text-sub shadow-sm ring-1 ring-brand-border">
          {totalMeals} món đã gợi ý
        </div>
      </div>

      <div className="space-y-5">
        {meals.map((meal) => (
          <section key={meal.title} className="glass-panel overflow-hidden p-0">
            <div className="flex flex-col gap-3 border-b border-brand-border bg-brand-surface/70 p-5 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex items-center gap-3">
                <span className={`h-12 w-2 rounded-full ${accentClass(meal.accent)}`} />
                <div>
                  <h3 className="text-xl font-black text-brand-text-main">{meal.title}</h3>
                  <p className="mt-1 text-sm font700 text-brand-text-sub">
                    {meal.items.length} món, ảnh đồng đều và macro rõ ràng
                  </p>
                </div>
              </div>
              <div className="rounded-2xl bg-brand-navy px-4 py-2 text-sm font900 text-white">
                {meal.items.reduce((sum, item) => sum + item.calories, 0)} kcal
              </div>
            </div>

            <div className="grid gap-4 p-4 sm:p-5 lg:grid-cols-2 2xl:grid-cols-3">
              {meal.items.map((item) => (
                <MealCard
                  key={item.id}
                  item={item}
                  favorite={favoriteMeals.has(item.id)}
                  rating={ratings[item.id]}
                  onFavorite={() => onFavorite(item.id)}
                  onRate={(value) => onRate(item.id, value)}
                />
              ))}
            </div>
          </section>
        ))}
      </div>
    </section>
  );
}

function accentClass(accent) {
  if (accent === "blue") return "bg-sky-500";
  if (accent === "orange") return "bg-brand-orange";
  return "bg-brand-primary";
}

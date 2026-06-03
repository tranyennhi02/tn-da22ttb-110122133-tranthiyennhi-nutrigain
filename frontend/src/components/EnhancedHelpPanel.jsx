import { useState } from "react";

// Help Icons
const HelpIcons = {
  Search: (props) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>,
  ChevronDown: (props) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="m6 9 6 6 6-6"/></svg>,
  MessageSquare: (props) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="m3 21 1.9-5.7a8.5 8.5 0 1 1 3.8 3.8z"/></svg>,
  BookOpen: (props) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></svg>,
  Activity: (props) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>,
  AlertCircle: (props) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>,
  Lightbulb: (props) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A6 6 0 0 0 6 8c0 1 .2 2.2 1.5 3.5.7.7 1.3 1.5 1.5 2.5"/><path d="M9 18h6"/><path d="M10 22h4"/></svg>,
  HelpCircle: (props) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>,
  CheckCircle: (props) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><circle cx="12" cy="12" r="9"/><path d="m9 12 2 2 4-4"/></svg>
};

export default function EnhancedHelpPanel({ foods }) {
  console.log("[ENHANCED HELP PANEL RENDERED]");
  
  const [searchQuery, setSearchQuery] = useState("");
  const [activeCategory, setActiveCategory] = useState("all");
  const [expandedFaq, setExpandedFaq] = useState(null);
  
  const [report, setReport] = useState({ item: "", type: "wrong_image", description: "" });
  const [submitted, setSubmitted] = useState(false);

  // Core FAQ - only 8 most important questions
  const faqs = [
    { id: 'faq-0', category: 'profile', title: 'Hệ thống dành cho ai?', answer: 'NutriGain hỗ trợ người muốn tăng cân lành mạnh, đặc biệt khi BMI dưới 18.5 theo chuẩn châu Á.' },
    { id: 'faq-1', category: 'profile', title: 'Vì sao BMI >= 18.5 không sinh thực đơn?', answer: 'Hệ thống tập trung cho mục tiêu tăng cân thiếu cân. Nếu BMI đã bình thường, bạn có thể cập nhật hồ sơ hoặc theo dõi nhật ký ăn uống.' },
    { id: 'faq-2', category: 'profile', title: 'Cách cập nhật cân nặng và tạo lại thực đơn?', answer: 'Vào "Tài khoản", cập nhật cân nặng và nhấn "Cập nhật và tạo lại thực đơn". Calories sẽ được tính lại.' },
    { id: 'faq-3', category: 'menu', title: 'Cách đổi món trong thực đơn?', answer: 'Vào thực đơn hôm nay, chọn món muốn đổi và dùng chức năng đổi món nếu có.' },
    { id: 'faq-4', category: 'menu', title: 'Làm sao đánh dấu "Đã ăn"?', answer: 'Click vào thẻ món ăn hoặc nút tick để xác nhận đã ăn. Calories sẽ được cộng dồn trong ngày.' },
    { id: 'faq-5', category: 'data', title: 'Vì sao ảnh món ăn có thể chỉ là ảnh minh họa?', answer: 'Hệ thống dùng dataset tĩnh để tối ưu tốc độ. Một số món chưa có ảnh thật sẽ dùng placeholder.' },
    { id: 'faq-6', category: 'data', title: 'Nếu ảnh nhận diện sai thì làm gì?', answer: 'Bạn có thể xóa nguyên liệu nhận sai và nhập thủ công nguyên liệu đúng.' },
    { id: 'faq-7', category: 'account', title: 'Xuất báo cáo dinh dưỡng ở đâu?', answer: 'Vào trang "Tài khoản" và chọn "Xuất CSV" để tải báo cáo dinh dưỡng chi tiết.' }
  ];

  const filteredFaqs = faqs.filter(faq => {
    const matchesSearch = faq.title.toLowerCase().includes(searchQuery.toLowerCase()) || faq.answer.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory = activeCategory === "all" || faq.category === activeCategory;
    return matchesSearch && matchesCategory;
  });

  function submitReport(event) {
    event.preventDefault();
    if (!report.description.trim()) return;
    setSubmitted(true);
    setTimeout(() => {
      setSubmitted(false);
      setReport({ item: "", type: "wrong_image", description: "" });
    }, 5000);
  }

  const handleScrollTo = (id) => {
    const el = document.getElementById(id);
    if(el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  return (
    <div id="help-panel" data-help-ui-version="v2" className="space-y-6 pb-20">
      <div data-help-ui-version="v2" className="sr-only">HELP_UI_V2</div>
      
      {/* Compact Hero */}
      <section className="glass-panel relative overflow-hidden bg-gradient-to-br from-emerald-600 to-teal-600 px-6 py-10 sm:px-10 sm:py-12 shadow-sm">
        <div className="relative z-10 mx-auto max-w-3xl">
          <h1 className="text-3xl sm:text-4xl font-black text-white">Hỗ trợ NutriGain</h1>
          <p className="mt-3 text-base sm:text-lg font800 text-emerald-50">Tìm hướng dẫn sử dụng, câu hỏi thường gặp hoặc gửi phản hồi cho chúng tôi.</p>
          
          <div className="mt-6 relative">
            <HelpIcons.Search className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-slate-400" />
            <input 
              type="text" 
              placeholder="Tìm câu hỏi, ví dụ: BMI, đổi món, cập nhật cân nặng..." 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="h-12 w-full rounded-xl border-0 bg-white pl-12 pr-4 text-sm font800 text-slate-900 shadow-sm outline-none placeholder:text-slate-400 focus:ring-2 focus:ring-white/50 transition-all"
            />
          </div>
        </div>
      </section>

      {/* Support Topic Cards */}
      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[
          { icon: HelpIcons.HelpCircle, title: "Hồ sơ & BMI", desc: "Cập nhật chiều cao, cân nặng và kiểm tra điều kiện tạo thực đơn.", category: "profile" },
          { icon: HelpIcons.BookOpen, title: "Thực đơn", desc: "Tạo thực đơn, đổi món và hiểu cách hệ thống gợi ý món ăn.", category: "menu" },
          { icon: HelpIcons.Activity, title: "Nhật ký ăn uống", desc: "Đánh dấu đã ăn, theo dõi kcal và xem tiến độ hôm nay.", category: "menu" },
          { icon: HelpIcons.Lightbulb, title: "Ảnh món ăn", desc: "Tải ảnh nguyên liệu và xử lý khi nhận diện chưa chính xác.", category: "data" }
        ].map((topic, idx) => (
          <button
            key={idx}
            onClick={() => { setActiveCategory(topic.category); handleScrollTo("faq-section"); }}
            className="glass-panel p-5 text-left hover:shadow-md hover:scale-[1.02] transition-all group"
          >
            <topic.icon className="h-7 w-7 text-emerald-600 mb-3 group-hover:scale-110 transition-transform" />
            <h3 className="text-base font-black text-slate-900 mb-1.5">{topic.title}</h3>
            <p className="text-xs font800 text-slate-600 leading-relaxed">{topic.desc}</p>
          </button>
        ))}
      </section>

      {/* Main Content - 2 Columns */}
      <div className="grid gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)] items-start">
        
        {/* Left Column: FAQ */}
        <div className="space-y-6">
          
          {/* FAQ Section */}
          <section id="faq-section" className="glass-panel p-6 shadow-sm">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-2">
                <HelpIcons.HelpCircle className="h-6 w-6 text-emerald-600" />
                <h2 className="text-2xl font-black text-slate-900">Câu hỏi thường gặp</h2>
              </div>
              <span className="text-sm font800 text-slate-500">{filteredFaqs.length} câu hỏi</span>
            </div>
            
            {filteredFaqs.length === 0 ? (
              <div className="text-center py-12">
                <HelpIcons.Search className="mx-auto h-14 w-14 text-slate-300 mb-3" />
                <p className="text-lg font900 text-slate-600">Không tìm thấy nội dung phù hợp</p>
                <p className="text-sm font800 text-slate-500 mt-2">Hãy thử từ khóa khác hoặc gửi phản hồi bên phải</p>
              </div>
            ) : (
              <div className="space-y-3">
                {filteredFaqs.map(faq => {
                  const isExpanded = expandedFaq === faq.id;
                  return (
                    <div key={faq.id} className={`rounded-xl border-2 transition-all ${isExpanded ? 'border-emerald-300 bg-emerald-50/60 shadow-sm' : 'border-slate-150 bg-white hover:border-emerald-200'}`}>
                      <button 
                        onClick={() => setExpandedFaq(isExpanded ? null : faq.id)}
                        className="w-full flex items-center justify-between p-4 text-left focus:outline-none"
                      >
                        <span className="font900 text-base text-slate-900 pr-4">{faq.title}</span>
                        <span className={`flex-shrink-0 text-emerald-600 transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}`}>
                          <HelpIcons.ChevronDown className="h-5 w-5" />
                        </span>
                      </button>
                      {isExpanded && (
                        <div className="px-4 pb-4 animate-fade-in text-sm font800 text-slate-700 leading-relaxed">
                          {faq.answer}
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            )}
          </section>

          {/* Quick Guide - Compact 3 Steps */}
          <section className="glass-panel p-6 shadow-sm">
            <div className="flex items-center gap-2 mb-5">
              <HelpIcons.BookOpen className="h-6 w-6 text-emerald-600" />
              <h2 className="text-xl font-black text-slate-900">Hướng dẫn nhanh</h2>
            </div>
            
            <div className="grid sm:grid-cols-3 gap-4">
              {[
                { num: "1", title: "Cập nhật hồ sơ", desc: "Nhập chiều cao, cân nặng để tính BMI và calories" },
                { num: "2", title: "Tạo thực đơn", desc: "Hệ thống sinh thực đơn tăng cân phù hợp" },
                { num: "3", title: "Đánh dấu đã ăn", desc: "Theo dõi tiến độ và cập nhật định kỳ" }
              ].map((step) => (
                <div key={step.num} className="relative rounded-xl bg-gradient-to-br from-emerald-50 to-teal-50 p-5 border border-emerald-100">
                  <div className="flex items-center justify-center w-10 h-10 rounded-full bg-emerald-600 text-white font-black text-lg mb-3">
                    {step.num}
                  </div>
                  <h3 className="font-black text-sm text-slate-900 mb-1.5">{step.title}</h3>
                  <p className="text-xs font800 text-slate-600 leading-relaxed">{step.desc}</p>
                </div>
              ))}
            </div>
          </section>

        </div>

        {/* Right Column: Feedback & Status */}
        <div className="space-y-6">
          
          {/* Feedback Form */}
          <div id="feedback-form" className="glass-panel p-6 shadow-sm relative overflow-hidden">
             <div className="absolute top-0 right-0 w-28 h-28 bg-emerald-500/10 rounded-full blur-3xl -mr-12 -mt-12"></div>
             <div className="relative z-10">
               <h3 className="text-xl font-black text-slate-950 mb-2">Gửi phản hồi</h3>
               <p className="text-sm font800 text-slate-600 mb-5">Gặp vấn đề? Cho chúng tôi biết để cải thiện.</p>
               
               <form className="space-y-4" onSubmit={submitReport}>
                  <div>
                    <label className="block text-xs font900 text-slate-700 mb-2">Loại vấn đề</label>
                    <select
                      className="h-11 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm font800 text-slate-800 outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20 transition"
                      value={report.type}
                      onChange={(e) => setReport({ ...report, type: e.target.value })}
                    >
                      <option value="wrong_image">Ảnh món ăn sai</option>
                      <option value="abnormal_macro">Dữ liệu dinh dưỡng sai</option>
                      <option value="not_working">Lỗi không sinh được thực đơn</option>
                      <option value="ui_glitch">Giao diện lỗi/Hỏng</option>
                      <option value="other">Vấn đề khác</option>
                    </select>
                  </div>
                  
                  <div>
                    <label className="block text-xs font900 text-slate-700 mb-2">Vị trí / Tên món (tùy chọn)</label>
                    <input
                      className="h-11 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm font800 text-slate-800 outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20 transition"
                      list="food-report-options"
                      placeholder="VD: Phở bò, trang Tài khoản"
                      value={report.item}
                      onChange={(e) => setReport({ ...report, item: e.target.value })}
                    />
                    {foods && foods.length > 0 && (
                      <datalist id="food-report-options">
                        {foods.slice(0, 80).map((food) => (
                          <option key={food.id} value={food.name} />
                        ))}
                      </datalist>
                    )}
                  </div>

                  <div>
                    <label className="block text-xs font900 text-slate-700 mb-2">Mô tả chi tiết *</label>
                    <textarea
                      required
                      className="min-h-28 w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm font800 text-slate-800 outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20 transition resize-none"
                      placeholder="Vui lòng cung cấp chi tiết..."
                      value={report.description}
                      onChange={(e) => setReport({ ...report, description: e.target.value })}
                    />
                  </div>

                  <button type="submit" className="flex w-full items-center justify-center gap-2 h-12 rounded-xl bg-slate-950 px-4 text-sm font900 text-white hover:bg-slate-800 active:scale-[0.98] transition">
                    <HelpIcons.MessageSquare className="h-4 w-4" /> Gửi phản hồi
                  </button>

                  {submitted && (
                    <div className="rounded-xl bg-emerald-50 p-3 border border-emerald-200 animate-fade-in flex items-start gap-2">
                      <HelpIcons.CheckCircle className="h-4 w-4 text-emerald-600 mt-0.5 shrink-0" />
                      <p className="text-xs font900 text-emerald-800 leading-tight">Đã ghi nhận phản hồi. Cảm ơn bạn!</p>
                    </div>
                  )}
               </form>
             </div>
          </div>

          {/* System Status */}
          <div className="glass-panel p-5 shadow-sm">
             <div className="flex items-center gap-2 mb-4">
                <HelpIcons.Activity className="h-5 w-5 text-slate-900" />
                <h3 className="text-base font900 text-slate-900">Tình trạng hệ thống</h3>
             </div>
             <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font800 text-slate-600">Dữ liệu món ăn</span>
                  <span className="flex items-center gap-1.5 text-xs font900 text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-lg">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>Sẵn sàng
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs font800 text-slate-600">Thuật toán sinh menu</span>
                  <span className="flex items-center gap-1.5 text-xs font900 text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-lg">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>Hoạt động
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs font800 text-slate-600">Đồng bộ nhật ký</span>
                  <span className="flex items-center gap-1.5 text-xs font900 text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-lg">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>Hoạt động
                  </span>
                </div>
             </div>
          </div>

        </div>
      </div>
    </div>
  );
}

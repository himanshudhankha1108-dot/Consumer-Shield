

const PredefinedCases = {
  blank: {
    caseId: "CS-CUSTOM-001",
    product: "Custom Dispute (Awaiting Evidence)",
    seller: "Awaiting Invoice Details",
    disputeType: "defective_product",
    score: 0,
    purchaseDate: "Not Established",
    warrantyText: "Awaiting Warranty Doc",
    filesCountText: "0 Documents Uploaded",
    hasConflict: false,
    conflicts: [],
    facts: [],
    timeline: [],
    checklist: [
      { name: "Proof of Purchase (Invoice)", category: "Purchase Evidence", file: "None", status: "missing" },
      { name: "Manufacturer Warranty Document", category: "Warranty Evidence", file: "None", status: "missing" },
      { name: "Written Complaint to Seller", category: "Communication", file: "None", status: "missing" },
      { name: "Photographic Evidence of Defect", category: "Defect Proof", file: "None", status: "missing" }
    ],
    dimensions: [
      { name: "Essential Purchase Evidence", score: 0, max: 25, color: "text-rose-400" },
      { name: "Warranty & Policy Terms", score: 0, max: 20, color: "text-rose-400" },
      { name: "Defect & Damage Proof", score: 0, max: 20, color: "text-rose-400" },
      { name: "Communication History", score: 0, max: 20, color: "text-rose-400" },
      { name: "Timeline Completeness", score: 0, max: 15, color: "text-rose-400" }
    ],
    rules: [
      {
        name: "Awaiting Document Upload",
        status: "PRECONDITION_REQUIRED",
        badgeColor: "bg-slate-500/15 text-slate-300 border-slate-500/25",
        text: "Please upload a purchase invoice, warranty card, or communication screenshot to evaluate legal windows."
      }
    ],
    policies: [
      {
        title: "Consumer Protection Act, 2019",
        tag: "General Protection",
        quote: "Statutory provisions will be mapped once product and purchase details are verified in the ledger."
      }
    ],
    complaintDraft: "Awaiting sufficient facts to compile a formal grievance draft. Please upload purchase proof and defect description."
  },

  boat: {
    caseId: "CS-2026-X4",
    product: "Boat Rockerz 450",
    seller: "RetailNet Online (Flipkart)",
    disputeType: "defective_product",
    score: 75,
    purchaseDate: "10 Jan 2026",
    warrantyText: "12 Months (Within Window)",
    filesCountText: "4 Documents",
    hasConflict: true,
    conflicts: [
      {
        field: "purchase_date",
        options: [
          { value: "2026-01-10", source: "Invoice (Flipkart_Invoice.pdf)", confidence: 0.99 },
          { value: "2026-01-14", source: "Email (Customer_Query.eml)", confidence: 0.82 }
        ]
      }
    ],
    facts: [
      { field: "product_name", value: "Boat Rockerz 450", source: "Invoice (Flipkart_Invoice.pdf)", confidence: 0.98, status: "verified" },
      { field: "seller_name", value: "RetailNet Online", source: "Invoice (Flipkart_Invoice.pdf)", confidence: 0.96, status: "verified" },
      { field: "purchase_date", value: "2026-01-10", source: "Invoice (Flipkart_Invoice.pdf)", confidence: 0.99, status: "conflicting" },
      { field: "purchase_date", value: "2026-01-14", source: "Email (Customer_Query.eml)", confidence: 0.82, status: "conflicting" },
      { field: "warranty_period_months", value: "12 Months", source: "Warranty_Card (Warranty_Booklet.pdf)", confidence: 0.95, status: "verified" },
      { field: "defect_date", value: "2026-02-15", source: "WhatsApp (WhatsApp_Chat.txt)", confidence: 0.90, status: "verified" },
      { field: "seller_response", value: "Claim rejected citing customer wear", source: "Email (Brand_Rejection.pdf)", confidence: 0.95, status: "verified" }
    ],
    timeline: [
      { icon: "shopping-bag", type: "Purchase Completed", date: "10 Jan 2026", desc: "Ordered Boat Rockerz 450 on Flipkart for ₹1,499", file: "Flipkart_Invoice.pdf" },
      { icon: "truck", type: "Order Delivered", date: "13 Jan 2026", desc: "Delivered via Ekart Logistics with intact packaging", file: "Flipkart_Invoice.pdf" },
      { icon: "alert-triangle", type: "Defect Discovered", date: "15 Feb 2026", desc: "Left ear-cup stopped charging and emitting audio", file: "WhatsApp_Chat.txt" },
      { icon: "mail", type: "Grievance Raised", date: "16 Feb 2026", desc: "Ticket logged with Imagine Marketing (Boat) customer support", file: "Customer_Query.eml" },
      { icon: "x-circle", type: "Claim Denied", date: "20 Feb 2026", desc: "Service Center rejected warranty coverage citing alleged wear", file: "Brand_Rejection.pdf" }
    ],
    checklist: [
      { name: "Proof of Purchase (Invoice)", category: "Purchase Evidence", file: "Flipkart_Invoice.pdf", status: "found" },
      { name: "Manufacturer Warranty Document", category: "Warranty Evidence", file: "Warranty_Booklet.pdf", status: "found" },
      { name: "Written Complaint / Communication", category: "Communication", file: "Customer_Query.eml", status: "found" },
      { name: "Seller / Brand Denial Response", category: "Communication", file: "Brand_Rejection.pdf", status: "found" },
      { name: "Photographic Evidence of Defect", category: "Defect Proof", file: "None", status: "missing" },
      { name: "Authorized Service Inspection Job Sheet", category: "Inspection", file: "None", status: "partial" }
    ],
    dimensions: [
      { name: "Essential Purchase Evidence", score: 25, max: 25, color: "text-emerald-400" },
      { name: "Warranty & Policy Terms", score: 20, max: 20, color: "text-emerald-400" },
      { name: "Defect & Damage Proof", score: 5, max: 20, color: "text-rose-400" },
      { name: "Communication History", score: 15, max: 20, color: "text-amber-400" },
      { name: "Timeline Completeness", score: 10, max: 15, color: "text-cyan-400" }
    ],
    rules: [
      {
        name: "Warranty Coverage Window (12 Months)",
        status: "PASSED",
        badgeColor: "bg-emerald-500/15 text-emerald-300 border-emerald-500/25",
        text: "Purchase: 2026-01-10 | Defect: 2026-02-15. Defect occurred 36 days after purchase, well within 365-day warranty (329 days remaining)."
      },
      {
        name: "Statutory Limitation Check (2 Years)",
        status: "ACTIVE",
        badgeColor: "bg-emerald-500/15 text-emerald-300 border-emerald-500/25",
        text: "Cause of action arose on 2026-02-15. Complaint is valid for filing before District Commission until 2028-02-15 under Section 69, Consumer Protection Act."
      }
    ],
    policies: [
      {
        title: "Consumer Protection Act, 2019 — Sec 2(12)",
        tag: "Effective 2020-07-20",
        quote: "Defect means any fault, imperfection or shortcoming in the quality, quantity, potency, purity or standard required to be maintained under any contract or law."
      },
      {
        title: "E-Commerce Rules, 2020 — Rule 6(3)",
        tag: "Duties of Sellers",
        quote: "No seller offering goods on marketplace shall refuse to take back goods, or withdraw or discontinue services, if such goods are defective, deficient or spurious."
      }
    ],
    complaintDraft: `To,\nThe Grievance Redressal Officer\nRetailNet Online / Imagine Marketing Ltd. (boAt)\nVia: Online Dispute Portal & Consumer Grievance Cell\n\nSubject: FORMAL NOTICE: Unlawful Warranty Rejection for Defective boAt Rockerz 450 (Invoice Date: 10/01/2026)\n\nDear Sir / Madam,\n\nI am writing to issue a formal grievance regarding my purchase of "Boat Rockerz 450" (Order/Invoice: Flipkart_Invoice.pdf) purchased on 10 January 2026 for ₹1,499.\n\nFACTUAL CHRONOLOGY:\n1. 10 Jan 2026: Product purchased online via authorized channel.\n2. 13 Jan 2026: Product successfully delivered in sealed box.\n3. 15 Feb 2026: The left speaker abruptly ceased functioning and stopped taking a battery charge (36 days after purchase).\n4. 16 Feb 2026: Formal repair/replacement request initiated via email.\n5. 20 Feb 2026: Claim summarily denied by service center citing arbitrary physical wear, without technical inspection.\n\nSTATUTORY VIOLATIONS & LEGAL RIGHTS:\n1. The defect manifested well within the 12-month manufacturer comprehensive warranty period (expires 10 Jan 2027).\n2. Under Section 2(12) of the Consumer Protection Act, 2019, any imperfection or shortcoming in standard performance constitutes an actionable "Defect".\n3. Under Rule 6(3) of the Consumer Protection (E-Commerce) Rules, 2020, marketplace sellers are legally obligated to honor warranty commitments and cannot refuse remedy for inherently defective goods.\n\nREQUESTED RELIEF:\nI hereby demand an immediate free-of-cost replacement unit or a full refund of ₹1,499 within seven (7) business days. Failing this, I shall proceed to lodge a formal complaint before the National Consumer Helpline (NCH) and the competent District Consumer Disputes Redressal Commission.\n\nSincerely,\nAggrieved Consumer\n(Contact & Proof of Purchase Attached)`
  },

  samsung: {
    caseId: "CS-2026-SAM",
    product: "Samsung Crystal 4K 43\" TV",
    seller: "Cloudtail India (Amazon)",
    disputeType: "warranty_rejection",
    score: 85,
    purchaseDate: "01 Feb 2026",
    warrantyText: "12 + 12 Months Panel Warranty",
    filesCountText: "5 Documents",
    hasConflict: true,
    conflicts: [
      {
        field: "purchase_date",
        options: [
          { value: "2026-02-01", source: "Invoice (sample_invoice_samsung_tv.txt)", confidence: 0.99 },
          { value: "2026-02-05", source: "Email (sample_contradictory_customer_email.txt)", confidence: 0.84 }
        ]
      }
    ],
    facts: [
      { field: "product_name", value: "Samsung 4K Vivid Pro (UA43CUE60AKLXL)", source: "sample_invoice_samsung_tv.txt", confidence: 0.99, status: "verified" },
      { field: "seller_name", value: "Cloudtail India Pvt Ltd", source: "sample_invoice_samsung_tv.txt", confidence: 0.98, status: "verified" },
      { field: "purchase_date", value: "2026-02-01", source: "sample_invoice_samsung_tv.txt", confidence: 0.99, status: "conflicting" },
      { field: "purchase_date", value: "2026-02-05", source: "sample_contradictory_customer_email.txt", confidence: 0.84, status: "conflicting" },
      { field: "warranty_period_months", value: "12 Months (Panel: 24M)", source: "sample_warranty_card.txt", confidence: 0.97, status: "verified" },
      { field: "defect_date", value: "2026-02-18", source: "sample_whatsapp_support_chat.txt", confidence: 0.95, status: "verified" },
      { field: "amount_paid", value: "₹34,208.20", source: "sample_invoice_samsung_tv.txt", confidence: 0.99, status: "verified" },
      { field: "seller_response", value: "Claim rejected: ₹19,500 repair bill demanded", source: "sample_brand_denial_email.txt", confidence: 0.96, status: "verified" }
    ],
    timeline: [
      { icon: "shopping-bag", type: "Purchase Completed", date: "01 Feb 2026", desc: "Purchased Samsung 43\" Smart TV via Amazon India for ₹34,208", file: "sample_invoice_samsung_tv.txt" },
      { icon: "truck", type: "Order Delivered", date: "04 Feb 2026", desc: "Delivered in sealed package by Cloudtail logistics", file: "sample_invoice_samsung_tv.txt" },
      { icon: "alert-triangle", type: "Defect Discovered", date: "18 Feb 2026", desc: "Horizontal and vertical green lines distorted display panel", file: "sample_whatsapp_support_chat.txt" },
      { icon: "mail", type: "Support Escalation", date: "18 Feb 2026", desc: "Chat logged with Amazon support (Ticket #AMZ-IN-889123)", file: "sample_whatsapp_support_chat.txt" },
      { icon: "x-circle", type: "Service Rejection", date: "24 Feb 2026", desc: "Samsung center alleged physical stress and demanded ₹19,500 + tax", file: "sample_brand_denial_email.txt" }
    ],
    checklist: [
      { name: "Original Tax Invoice", category: "Purchase Evidence", file: "sample_invoice_samsung_tv.txt", status: "found" },
      { name: "Official Warranty Certificate", category: "Warranty Evidence", file: "sample_warranty_card.txt", status: "found" },
      { name: "Customer Grievance Thread", category: "Communication", file: "sample_whatsapp_support_chat.txt", status: "found" },
      { name: "Service Center Rejection Letter", category: "Inspection", file: "sample_brand_denial_email.txt", status: "found" },
      { name: "High-Resolution Display Photo", category: "Defect Proof", file: "None", status: "missing" }
    ],
    dimensions: [
      { name: "Essential Purchase Evidence", score: 25, max: 25, color: "text-emerald-400" },
      { name: "Warranty & Policy Terms", score: 20, max: 20, color: "text-emerald-400" },
      { name: "Defect & Damage Proof", score: 10, max: 20, color: "text-amber-400" },
      { name: "Communication History", score: 20, max: 20, color: "text-emerald-400" },
      { name: "Timeline Completeness", score: 10, max: 15, color: "text-cyan-400" }
    ],
    rules: [
      {
        name: "Manufacturer Warranty Window (12 Months)",
        status: "PASSED",
        badgeColor: "bg-emerald-500/15 text-emerald-300 border-emerald-500/25",
        text: "Purchase: 2026-02-01 | Defect: 2026-02-18. 17 days elapsed. TV is well within the 365-day manufacturer warranty (348 days remaining)."
      },
      {
        name: "7-Day E-Commerce Replacement Window",
        status: "EXPIRED",
        badgeColor: "bg-amber-500/15 text-amber-300 border-amber-500/25",
        text: "Delivered 2026-02-04, defect on 2026-02-18 (14 days elapsed). Platform 7-day replacement closed. Remedy must be pursued under Samsung Manufacturer Warranty."
      },
      {
        name: "Limitation Period (CPA Sec 69)",
        status: "ACTIVE",
        badgeColor: "bg-emerald-500/15 text-emerald-300 border-emerald-500/25",
        text: "Cause of action: 2026-02-18. Actionable before District Consumer Commission until 2028-02-18."
      }
    ],
    policies: [
      {
        title: "Consumer Protection Act, 2019 — Section 84",
        tag: "Product Liability of Manufacturer",
        quote: "A product manufacturer shall be liable in a product liability action if the product contains a manufacturing defect, design flaw, or fails to conform to express warranty."
      },
      {
        title: "Consumer Protection Act, 2019 — Section 2(11)",
        tag: "Deficiency in Service",
        quote: "Summary rejection of warranty claims without an objective technical laboratory test constitutes an actionable deficiency in service."
      }
    ],
    complaintDraft: `To,\nThe Grievance Redressal Officer\nSamsung India Electronics Pvt. Ltd. & Cloudtail India\n\nSubject: LEGAL NOTICE: Arbitrary Warranty Repudiation for Samsung 43" Smart TV (Model: UA43CUE60AKLXL)\n\nDear Sir / Madam,\n\nI am issuing this formal notice concerning invoice INV-BLR-2026-88912 dated 01 February 2026 for Samsung Crystal 4K Smart TV purchased for ₹34,208.20.\n\nWithin 17 days of purchase (18 Feb 2026), the display panel manifested severe green line artifacts without any impact, drop, or liquid contact. In violation of statutory consumer protection guidelines, your service center (Ticket #SMC-BLR-2026-90412) summarily dismissed the warranty claim and demanded an unlawful payment of ₹19,500 + GST for panel replacement.\n\nSTATUTORY LIABILITIES:\n1. Under Section 84 of the Consumer Protection Act 2019, product manufacturers are strictly liable for manufacturing defects and non-conformance to express warranties.\n2. Blanket rejection without an objective technical test report constitutes an actionable 'Deficiency in Service' under Section 2(11).\n\nDEMAND:\nI demand an unconditional zero-cost panel replacement or full invoice refund of ₹34,208.20 within 7 days, failing which this matter will be escalated to the National Consumer Helpline and the District Consumer Forum.\n\nSincerely,\nRahul Sharma`
  },

  nike: {
    caseId: "CS-2026-NK9",
    product: "Nike Air Zoom Running Shoes",
    seller: "FashionTrend India (Flipkart)",
    disputeType: "wrong_product",
    score: 95,
    purchaseDate: "05 Feb 2026",
    warrantyText: "7-Day Return / Replacement Policy",
    filesCountText: "3 Documents",
    hasConflict: false,
    conflicts: [],
    facts: [
      { field: "product_name", value: "Nike Air Zoom Pegasus (Size 9)", source: "Order_Invoice.pdf", confidence: 0.99, status: "verified" },
      { field: "seller_name", value: "FashionTrend India", source: "Order_Invoice.pdf", confidence: 0.98, status: "verified" },
      { field: "purchase_date", value: "2026-02-05", source: "Order_Invoice.pdf", confidence: 0.99, status: "verified" },
      { field: "delivery_date", value: "2026-02-08", source: "Courier_Tracking.pdf", confidence: 0.98, status: "verified" },
      { field: "defect_date", value: "2026-02-08", source: "Unboxing_Photo.jpg", confidence: 0.97, status: "verified" },
      { field: "defect_description", value: "Received unbranded counterfeit shoes instead of Nike", source: "Customer_Complaint.eml", confidence: 0.95, status: "verified" }
    ],
    timeline: [
      { icon: "shopping-bag", type: "Order Placed", date: "05 Feb 2026", desc: "Ordered Nike Air Zoom shoes for ₹7,995", file: "Order_Invoice.pdf" },
      { icon: "truck", type: "Delivered", date: "08 Feb 2026", desc: "Package delivered by courier", file: "Courier_Tracking.pdf" },
      { icon: "alert-triangle", type: "Wrong Item Opened", date: "08 Feb 2026", desc: "Box contained counterfeit unbranded product", file: "Unboxing_Photo.jpg" },
      { icon: "mail", type: "Return Requested", date: "09 Feb 2026", desc: "Return lodged within 24 hours of delivery", file: "Customer_Complaint.eml" }
    ],
    checklist: [
      { name: "Original Purchase Invoice", category: "Purchase Evidence", file: "Order_Invoice.pdf", status: "found" },
      { name: "Courier Delivery Timestamp", category: "Timeline", file: "Courier_Tracking.pdf", status: "found" },
      { name: "Unboxing Photographic Proof", category: "Defect Proof", file: "Unboxing_Photo.jpg", status: "found" },
      { name: "Return Request Within 7 Days", category: "Communication", file: "Customer_Complaint.eml", status: "found" }
    ],
    dimensions: [
      { name: "Essential Purchase Evidence", score: 25, max: 25, color: "text-emerald-400" },
      { name: "Warranty & Policy Terms", score: 20, max: 20, color: "text-emerald-400" },
      { name: "Defect & Damage Proof", score: 20, max: 20, color: "text-emerald-400" },
      { name: "Communication History", score: 20, max: 20, color: "text-emerald-400" },
      { name: "Timeline Completeness", score: 10, max: 15, color: "text-cyan-400" }
    ],
    rules: [
      {
        name: "7-Day Platform Return / Replacement Window",
        status: "PASSED",
        badgeColor: "bg-emerald-500/15 text-emerald-300 border-emerald-500/25",
        text: "Delivered 2026-02-08 | Return lodged 2026-02-09. Only 1 day elapsed (6 days remaining in statutory 7-day replacement window)."
      },
      {
        name: "Factual Classification: Spurious / Non-Conforming Goods",
        status: "BREACHED BY SELLER",
        badgeColor: "bg-rose-500/15 text-rose-300 border-rose-500/25",
        text: "Goods delivered do not correspond to advertised brand description. Seller is strictly liable under e-commerce consumer guidelines."
      }
    ],
    policies: [
      {
        title: "E-Commerce Rules, 2020 — Rule 6(3)(b)",
        tag: "Spurious Goods Protection",
        quote: "No seller shall refuse to take back goods or refund consideration if the goods are not of the characteristics or features as advertised or are spurious."
      },
      {
        title: "Consumer Protection Act, 2019 — Section 2(47)",
        tag: "Unfair Trade Practice",
        quote: "Falsely representing that goods are of a particular standard, quality, grade or model constitutes an actionable unfair trade practice."
      }
    ],
    complaintDraft: `To,\nThe Grievance Redressal Officer\nFlipkart Internet Pvt. Ltd.\n\nSubject: URGENT: Delivery of Wrong / Spurious Goods (Order #OD-902138402)\n\nDear Sir / Madam,\n\nI received order #OD-902138402 on 08 Feb 2026. Instead of the ordered "Nike Air Zoom Pegasus" (₹7,995), the box contained an unbranded counterfeit footwear product.\n\nUnder Rule 6(3) of Consumer Protection (E-Commerce) Rules 2020, marketplace sellers cannot refuse immediate refund or replacement for wrong or spurious goods delivered. Immediate pickup and 100% refund is requested within 48 hours.\n\nSincerely,\nCustomer`
  }
};

let CurrentCase = JSON.parse(JSON.stringify(PredefinedCases.boat));

document.addEventListener("DOMContentLoaded", () => {
  renderAll();
  setupEventListeners();
  if (window.lucide) {
    lucide.createIcons();
  }
});

function renderAll() {
  updateHeaderStats();
  renderConflictBanner();
  renderUploadedFiles();
  renderFactsTable();
  renderTimeline();
  renderGapAnalysis();
  renderRulesAndPolicies();
  renderComplaintDraft();
  updateGauges();
  if (window.lucide) {
    lucide.createIcons();
  }
}

function updateHeaderStats() {
  const badge = document.getElementById("case-id-badge");
  const statProd = document.getElementById("stat-product");
  const statSeller = document.getElementById("stat-seller");
  const statDates = document.getElementById("stat-dates");
  const statWarranty = document.getElementById("stat-warranty");
  const statFiles = document.getElementById("stat-files-count");
  const statScoreText = document.getElementById("stat-score-text");

  if (badge) badge.textContent = CurrentCase.caseId;
  if (statProd) statProd.textContent = CurrentCase.product;
  if (statSeller) statSeller.textContent = CurrentCase.seller;
  if (statDates) statDates.textContent = CurrentCase.purchaseDate;
  if (statWarranty) statWarranty.textContent = CurrentCase.warrantyText;
  if (statFiles) statFiles.textContent = CurrentCase.filesCountText;
  if (statScoreText) statScoreText.textContent = `${CurrentCase.score} / 100`;
}

function renderConflictBanner() {
  const container = document.getElementById("conflict-banner-container");
  if (!container) return;

  if (CurrentCase.conflicts && CurrentCase.conflicts.length > 0) {
    container.innerHTML = `
      <div class="space-y-3">
        <div class="flex items-center justify-between text-xs text-rose-300 px-1 font-semibold">
          <span class="flex items-center gap-1.5">
            <span class="w-2 h-2 rounded-full bg-rose-500 animate-ping"></span>
            Factual Inconsistencies Detected (${CurrentCase.conflicts.length} Unresolved Contradictions)
          </span>
          <span class="text-[11px] bg-rose-500/20 text-rose-300 px-2.5 py-0.5 rounded-full border border-rose-500/30">Action Required — Resolving unblocks 100% Readiness</span>
        </div>
        ${CurrentCase.conflicts.map((c) => `
          <div class="relative overflow-hidden p-4 rounded-2xl bg-gradient-to-r from-rose-950/40 via-red-950/20 to-transparent border border-rose-500/30 backdrop-blur-xl">
            <div class="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4">
              <div class="flex items-start gap-3">
                <div class="p-2 rounded-xl bg-rose-500/20 border border-rose-500/30 text-rose-400 shrink-0">
                  <i data-lucide="alert-triangle" class="w-5 h-5"></i>
                </div>
                <div>
                  <h4 class="font-display font-bold text-sm text-rose-200">Discrepancy in <code class="px-1.5 py-0.5 rounded bg-black/40 text-cyan-300 font-mono text-xs">${c.field}</code></h4>
                  <p class="text-xs text-slate-300 mt-0.5">Documents report differing values. Click the correct fact below to resolve:</p>
                </div>
              </div>

              <div class="flex flex-wrap items-center gap-2 w-full lg:w-auto bg-black/40 p-2 rounded-xl border border-white/[0.06]">
                ${(c.options || []).map((opt) => `
                  <button class="btn-resolve-opt flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/[0.05] hover:bg-cyan-500/20 hover:border-cyan-500/40 border border-white/[0.08] text-xs text-slate-200 transition"
                          data-field="${c.field}" data-val="${opt.value}">
                    <span class="font-mono text-white font-bold">${opt.value}</span>
                    <span class="text-[10px] text-cyan-300 bg-cyan-950/80 px-1.5 py-0.5 rounded">${opt.source || 'Doc'}</span>
                    <span class="text-[10px] text-emerald-400 font-bold">✓ Adopt</span>
                  </button>
                `).join('')}
              </div>
            </div>
          </div>
        `).join('')}
      </div>
    `;

    container.querySelectorAll(".btn-resolve-opt").forEach(btn => {
      btn.addEventListener("click", async () => {
        const field = btn.getAttribute("data-field");
        const chosenVal = btn.getAttribute("data-val");

        try {
          const resp = await fetch(`/api/cases/${CurrentCase.caseId}/resolve-conflict`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ field_name: field, chosen_value: chosenVal })
          });
          if (resp.ok) {
            const resData = await resp.json();
            if (resData.all_facts) CurrentCase.facts = resData.all_facts;
            if (resData.conflicts) CurrentCase.conflicts = resData.conflicts;
          }
        } catch (e) {
          console.warn("Backend conflict resolve warning:", e);
        }

        CurrentCase.facts = CurrentCase.facts.filter(f => !(f.field === field && f.value !== chosenVal));
        for (const f of CurrentCase.facts) {
          if (f.field === field) {
            f.status = "verified";
            f.confidence = 1.0;
          }
        }

        CurrentCase.conflicts = CurrentCase.conflicts.filter(c => c.field !== field);

        if (field === "product_name") CurrentCase.product = chosenVal;
        if (field === "seller_name") CurrentCase.seller = chosenVal;
        if (field === "purchase_date") CurrentCase.purchaseDate = chosenVal;

        renderAll();
      });
    });
  } else {
    container.innerHTML = "";
  }
}

function renderUploadedFiles() {
  const container = document.getElementById("uploaded-files-container");
  const chips = document.getElementById("uploaded-files-chips");
  const countEl = document.getElementById("uploaded-files-count");
  if (!container || !chips) return;

  if (!CurrentCase.uploadedFiles || CurrentCase.uploadedFiles.length === 0) {
    container.classList.add("hidden");
    return;
  }

  container.classList.remove("hidden");
  if (countEl) countEl.textContent = `${CurrentCase.uploadedFiles.length} Files`;

  chips.innerHTML = CurrentCase.uploadedFiles.map(file => {
    let icon = "file-text";
    const name = typeof file === "string" ? file : file.name;
    if (name.endsWith(".png") || name.endsWith(".jpg") || name.endsWith(".jpeg")) icon = "image";
    else if (name.endsWith(".pdf")) icon = "file";

    return `
      <div class="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.08] text-xs text-slate-200 transition group">
        <i data-lucide="${icon}" class="w-3.5 h-3.5 text-cyan-400"></i>
        <span class="font-mono text-xs max-w-[220px] truncate" title="${name}">${name}</span>
        <button class="btn-delete-artifact ml-1 p-0.5 rounded hover:bg-rose-500/20 text-slate-400 hover:text-rose-400 transition"
                data-filename="${name}" title="Delete file & purge its extracted facts">
          <i data-lucide="x" class="w-3.5 h-3.5"></i>
        </button>
      </div>
    `;
  }).join("");

  chips.querySelectorAll(".btn-delete-artifact").forEach(btn => {
    btn.addEventListener("click", async (e) => {
      e.stopPropagation();
      const fname = btn.getAttribute("data-filename");
      if (!fname) return;

      try {
        const delResp = await fetch(`/api/cases/${CurrentCase.caseId}/files/${encodeURIComponent(fname)}`, {
          method: "DELETE"
        });
        if (delResp.ok) {
          const delData = await delResp.json();
          if (delData.all_facts) CurrentCase.facts = delData.all_facts;
          if (delData.conflicts) CurrentCase.conflicts = delData.conflicts;
        }
      } catch (err) {
        console.warn("Delete API error:", err);
      }

      CurrentCase.uploadedFiles = CurrentCase.uploadedFiles.filter(f => (typeof f === 'string' ? f : f.name) !== fname);
      if (!CurrentCase.facts.some(f => f.source !== fname)) {
        CurrentCase.facts = CurrentCase.facts.filter(f => f.source !== fname);
      }

      const fieldGroups = {};
      for (const f of CurrentCase.facts) {
        if (f.status === "conflicting") {
          fieldGroups[f.field] = fieldGroups[f.field] || [];
          fieldGroups[f.field].push({ value: f.value, source: f.source, confidence: f.confidence });
        }
      }
      CurrentCase.conflicts = Object.keys(fieldGroups).map(field => ({
        field: field,
        options: fieldGroups[field]
      }));

      renderAll();
    });
  });

  if (window.lucide) lucide.createIcons();
}

let factsViewMode = "canonical";

function setFactsViewMode(mode) {
  factsViewMode = mode;
  renderFactsTable();
}
window.setFactsViewMode = setFactsViewMode;

function focusConflict(fieldName) {
  const el = document.getElementById("conflict-banner-container");
  if (el) {
    el.scrollIntoView({ behavior: "smooth", block: "center" });
    el.classList.add("ring-2", "ring-rose-500", "transition-all");
    setTimeout(() => el.classList.remove("ring-2", "ring-rose-500"), 2000);
  }
}
window.focusConflict = focusConflict;

function getCanonicalFacts(caseObj) {
  if (caseObj.canonical_facts && caseObj.canonical_facts.length > 0) {
    return caseObj.canonical_facts;
  }
  const facts = caseObj.facts || [];
  if (facts.length === 0) return [];

  const grouped = {};
  for (const f of facts) {
    if (!grouped[f.field]) grouped[f.field] = [];
    grouped[f.field].push(f);
  }

  const result = [];
  for (const field of Object.keys(grouped)) {
    const entries = grouped[field];
    const isConflict = (caseObj.conflicts || []).some(c => c.field === field);
    const sources = [...new Set(entries.map(e => e.source).filter(Boolean))];
    const maxConf = Math.max(...entries.map(e => e.confidence || 0.9));

    let canonicalVal = null;
    if (caseObj.resolved_facts && caseObj.resolved_facts[field]) {
      canonicalVal = caseObj.resolved_facts[field];
    } else {
      const sorted = [...entries].sort((a, b) => (b.confidence || 0) - (a.confidence || 0) || String(b.value).length - String(a.value).length);
      canonicalVal = sorted[0].value;
    }

    let status = "verified";
    if (isConflict) {
      status = "conflicting";
    } else if (entries.some(e => e.status === "unverified")) {
      status = "unverified";
    } else if (entries.some(e => e.status === "verified") || entries.length >= 2) {
      status = "verified";
    } else {
      status = entries[0].status || "verified";
    }

    result.push({
      field: field,
      value: canonicalVal,
      sources: sources,
      sources_count: sources.length,
      confidence: maxConf,
      status: status,
      raw_values: [...new Set(entries.map(e => e.value))]
    });
  }

  return result;
}

function renderFactsTable() {
  const tbody = document.getElementById("facts-table-body");
  if (!tbody) return;

  const btnCanonical = document.getElementById("btn-view-canonical");
  const btnAudit = document.getElementById("btn-view-audit");
  const descEl = document.getElementById("facts-view-description");
  const badgeEl = document.getElementById("facts-count-badge");
  const thVal = document.getElementById("th-value");
  const thSrc = document.getElementById("th-source");

  if (factsViewMode === "canonical") {
    if (btnCanonical) {
      btnCanonical.className = "px-2.5 py-1 rounded-md font-medium transition bg-cyan-500/20 text-cyan-300 border border-cyan-500/30";
    }
    if (btnAudit) {
      btnAudit.className = "px-2.5 py-1 rounded-md font-medium transition text-slate-400 hover:text-white";
    }
    if (descEl) {
      descEl.textContent = "Showing consolidated verified parameters. Multi-source extractions are corroborated into single canonical facts.";
    }
    if (thVal) thVal.textContent = "Canonical Resolved Value";
    if (thSrc) thSrc.textContent = "Corroborating Provenance";

    const canonicalList = getCanonicalFacts(CurrentCase);
    if (badgeEl) badgeEl.textContent = `${canonicalList.length} Canonical Facts`;

    if (canonicalList.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="5" class="py-8 text-center text-slate-500 text-xs">
            No facts logged yet in this case. Drop invoices, warranty cards, or complaints in the box below to start extracting.
          </td>
        </tr>
      `;
      return;
    }

    tbody.innerHTML = canonicalList.map(f => {
      let statusBadge = "";
      if (f.status === "conflicting") {
        statusBadge = `<button onclick="focusConflict('${f.field}')" class="px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-500/15 text-rose-300 border border-rose-500/30 flex items-center gap-1 w-max ml-auto hover:bg-rose-500/25 transition">
                         <span class="w-1.5 h-1.5 rounded-full bg-rose-400 animate-ping"></span> Resolve Conflict
                       </button>`;
      } else if (f.status === "unverified") {
        statusBadge = `<span class="px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-500/15 text-amber-300 border border-amber-500/30 flex items-center gap-1 w-max ml-auto">
                         <span class="w-1.5 h-1.5 rounded-full bg-amber-400"></span> Unverified
                       </span>`;
      } else {
        statusBadge = `<span class="px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 flex items-center gap-1 w-max ml-auto">
                         <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span> Verified
                       </span>`;
      }

      let provenanceHtml = "";
      if (f.sources && f.sources.length > 1) {
        if (f.status === "conflicting") {
          provenanceHtml = `<span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-rose-950/70 text-rose-300 border border-rose-500/30 text-xs font-mono font-medium cursor-help" title="Differing values across ${f.sources.length} sources: ${f.sources.join(', ')}">
                              <i data-lucide="alert-circle" class="w-3.5 h-3.5 text-rose-400"></i> ${f.sources.length} Differing Sources
                            </span>`;
        } else {
          provenanceHtml = `<span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-cyan-950/70 text-cyan-300 border border-cyan-500/30 text-xs font-mono font-medium cursor-help" title="Corroborated across ${f.sources.length} sources: ${f.sources.join(', ')}">
                              <i data-lucide="layers" class="w-3.5 h-3.5 text-cyan-400"></i> ${f.sources.length} Sources Corroborated
                            </span>`;
        }
      } else {
        const srcName = (f.sources && f.sources[0]) || f.source || "Extracted";
        provenanceHtml = `<span class="text-slate-300 text-xs font-mono truncate max-w-[200px] block" title="${srcName}">${srcName}</span>`;
      }

      const confColor = f.confidence < 0.5 ? "text-amber-400" : "text-slate-400";

      return `
        <tr class="hover:bg-white/[0.02] transition">
          <td class="py-3.5 px-5 font-mono text-cyan-300 font-medium">${f.field}</td>
          <td class="py-3.5 px-5 font-bold text-white max-w-[320px] truncate" title="${f.value}">${f.value}</td>
          <td class="py-3.5 px-5">${provenanceHtml}</td>
          <td class="py-3.5 px-5 ${confColor} font-mono font-bold">${Math.round(f.confidence * 100)}%</td>
          <td class="py-3.5 px-5 text-right">${statusBadge}</td>
        </tr>
      `;
    }).join("");

  } else {
    if (btnCanonical) {
      btnCanonical.className = "px-2.5 py-1 rounded-md font-medium transition text-slate-400 hover:text-white";
    }
    if (btnAudit) {
      btnAudit.className = "px-2.5 py-1 rounded-md font-medium transition bg-cyan-500/20 text-cyan-300 border border-cyan-500/30";
    }
    if (descEl) {
      descEl.textContent = "Showing granular per-document raw extractions and source file attribution (Audit Trail).";
    }
    if (thVal) thVal.textContent = "Extracted Value";
    if (thSrc) thSrc.textContent = "Source Artifact";

    if (badgeEl) badgeEl.textContent = `${CurrentCase.facts.length} Audited Facts`;

    if (CurrentCase.facts.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="5" class="py-8 text-center text-slate-500 text-xs">
            No facts logged yet in this case. Drop invoices, warranty cards, or complaints in the box below to start extracting.
          </td>
        </tr>
      `;
      return;
    }

    tbody.innerHTML = CurrentCase.facts.map(f => {
      let statusBadge = "";
      if (f.status === "conflicting") {
        statusBadge = `<span class="px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-500/15 text-rose-300 border border-rose-500/30 flex items-center gap-1 w-max ml-auto">
                         <span class="w-1.5 h-1.5 rounded-full bg-rose-400 animate-ping"></span> Conflicting
                       </span>`;
      } else if (f.status === "unverified") {
        statusBadge = `<span class="px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-500/15 text-amber-300 border border-amber-500/30 flex items-center gap-1 w-max ml-auto">
                         <span class="w-1.5 h-1.5 rounded-full bg-amber-400"></span> Unverified
                       </span>`;
      } else {
        statusBadge = `<span class="px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 flex items-center gap-1 w-max ml-auto">
                         <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span> Verified
                       </span>`;
      }

      const confColor = f.confidence < 0.5 ? "text-amber-400" : "text-slate-400";

      return `
        <tr class="hover:bg-white/[0.02] transition">
          <td class="py-3.5 px-5 font-mono text-cyan-300 font-medium">${f.field}</td>
          <td class="py-3.5 px-5 font-bold text-white max-w-[260px] truncate" title="${f.value}">${f.value}</td>
          <td class="py-3.5 px-5 text-slate-300 text-xs font-mono">${f.source}</td>
          <td class="py-3.5 px-5 ${confColor} font-mono font-bold">${Math.round(f.confidence * 100)}%</td>
          <td class="py-3.5 px-5 text-right">${statusBadge}</td>
        </tr>
      `;
    }).join("");
  }

  if (window.lucide) lucide.createIcons();
}

function renderTimeline() {
  const container = document.getElementById("timeline-container");
  if (!container) return;

  if (CurrentCase.timeline.length === 0) {
    container.innerHTML = `
      <div class="py-8 text-center text-slate-500 text-xs">
        Timeline is empty. Upload documents with purchase, delivery or defect dates to reconstruct the event chronology.
      </div>
    `;
    return;
  }

  container.innerHTML = CurrentCase.timeline.map((item) => {
    return `
      <div class="relative flex items-start gap-4 group">
        <div class="absolute -left-6 top-1 w-5 h-5 rounded-full bg-[#080C16] border-2 border-cyan-400 flex items-center justify-center shadow-lg shadow-cyan-500/30 group-hover:scale-125 transition duration-300">
          <div class="w-1.5 h-1.5 rounded-full bg-cyan-400"></div>
        </div>
        <div class="glass-card p-4 rounded-xl flex-1 border border-white/[0.06] hover:border-cyan-500/30 transition">
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-1 mb-1">
            <span class="font-display font-bold text-sm text-white">${item.type}</span>
            <span class="font-mono text-xs text-cyan-300 bg-cyan-950/60 px-2 py-0.5 rounded-md border border-cyan-500/20">${item.date}</span>
          </div>
          <p class="text-xs text-slate-300">${item.desc}</p>
          <div class="mt-2 text-[11px] text-slate-500 flex items-center gap-1">
            <i data-lucide="file-check" class="w-3.5 h-3.5"></i>
            <span>Verified via: ${item.file}</span>
          </div>
        </div>
      </div>
    `;
  }).join("");
}

function renderGapAnalysis() {
  const dimContainer = document.getElementById("dimensions-container");
  if (dimContainer) {
    dimContainer.innerHTML = CurrentCase.dimensions.map(d => {
      const pct = d.max > 0 ? Math.round((d.score / d.max) * 100) : 0;
      return `
        <div class="glass-card p-3.5 rounded-xl border border-white/[0.06]">
          <div class="flex items-center justify-between text-xs mb-1.5">
            <span class="font-semibold text-slate-200">${d.name}</span>
            <span class="font-bold ${d.color}">${d.score} / ${d.max} (${pct}%)</span>
          </div>
          <div class="w-full bg-slate-800/80 rounded-full h-2 overflow-hidden">
            <div class="bg-gradient-to-r from-cyan-500 to-indigo-500 h-2 rounded-full transition-all duration-700" style="width: ${pct}%"></div>
          </div>
        </div>
      `;
    }).join("");
  }

  const checkBody = document.getElementById("checklist-table-body");
  if (checkBody) {
    checkBody.innerHTML = CurrentCase.checklist.map(c => {
      let badge = '';
      if (c.status === 'found') {
        badge = '<span class="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/15 text-emerald-300 border border-emerald-500/25">Found</span>';
      } else if (c.status === 'partial') {
        badge = '<span class="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/15 text-amber-300 border border-amber-500/25">Partial / Optional</span>';
      } else {
        badge = '<span class="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-500/15 text-rose-300 border border-rose-500/25 animate-pulse">Missing</span>';
      }

      return `
        <tr class="hover:bg-white/[0.02] transition">
          <td class="py-3 px-5 font-semibold text-white">${c.name}</td>
          <td class="py-3 px-5 text-xs text-slate-400">${c.category}</td>
          <td class="py-3 px-5 text-xs font-mono text-cyan-300">${c.file}</td>
          <td class="py-3 px-5 text-right">${badge}</td>
        </tr>
      `;
    }).join("");
  }
}

function renderRulesAndPolicies() {
  const rulesContainer = document.getElementById("rules-engine-results");
  if (rulesContainer && CurrentCase.rules) {
    rulesContainer.innerHTML = CurrentCase.rules.map(r => `
      <div class="p-4 rounded-xl bg-white/[0.03] border border-white/[0.06] space-y-2">
        <div class="flex items-center justify-between text-xs font-semibold">
          <span class="text-slate-300">${r.name}</span>
          <span class="px-2 py-0.5 rounded-full text-[11px] font-bold border ${r.badgeColor}">${r.status}</span>
        </div>
        <p class="text-xs text-slate-300 leading-relaxed">${r.text}</p>
      </div>
    `).join("");
  }

  const policiesContainer = document.getElementById("statutory-policies-results");
  if (policiesContainer && CurrentCase.policies) {
    policiesContainer.innerHTML = CurrentCase.policies.map(p => `
      <div class="p-4 rounded-xl bg-white/[0.03] border border-white/[0.06] space-y-2">
        <div class="flex items-center justify-between text-xs">
          <span class="font-bold text-indigo-300">${p.title}</span>
          <span class="text-[10px] text-slate-400 bg-white/[0.04] px-1.5 py-0.5 rounded font-mono">${p.tag}</span>
        </div>
        <p class="text-xs text-slate-300 italic leading-relaxed">"${p.quote}"</p>
      </div>
    `).join("");
  }
}

function renderComplaintDraft() {
  const pre = document.getElementById("complaint-text-preview");
  if (pre) {
    pre.textContent = CurrentCase.complaintDraft;
  }
}

function updateGauges() {
  const score = CurrentCase.score;
  const miniPct = document.getElementById("mini-gauge-pct");
  const miniCircle = document.getElementById("mini-gauge-circle");
  const mainScore = document.getElementById("main-gauge-score");
  const mainCircle = document.getElementById("main-gauge-circle");

  if (miniPct) miniPct.textContent = `${score}%`;
  if (mainScore) mainScore.textContent = score;

  if (miniCircle) {
    const offset = 144.5 - (144.5 * (score / 100));
    miniCircle.style.strokeDashoffset = offset;
  }

  if (mainCircle) {
    const mainOffset = 465 - (465 * (score / 100));
    mainCircle.style.strokeDashoffset = mainOffset;
  }
}

function classifyDocumentRelevance(filename, text) {
  const lowerName = filename.toLowerCase();
  const lowerText = text.toLowerCase();

  const isAcademic = /exp\d|experiment|os_|oops|practical|semester|assignment|deadlock|cpu_scheduling|paging|lab_report/i.test(lowerName) ||
                     /operating system|deadlock|round robin|semaphore|fork\(\)|int main\(\)|assignment submission/i.test(lowerText);

  if (isAcademic) {
    return {
      isRelevant: false,
      reason: "Academic / Lab Experiment (No invoice, warranty, or consumer dispute data detected)",
      confidence: 0.15
    };
  }

  const hasConsumerKeywords = /invoice|tax invoice|gstin|warranty|flipkart|amazon|refund|defect|cash memo|serial no|order id|cloudtail|retailnet/i.test(lowerName) ||
                              /invoice|gstin|amount paid|warranty period|rejection|broken|crackling|defective/i.test(lowerText);

  if (hasConsumerKeywords) {
    return {
      isRelevant: true,
      reason: "Verified Consumer Dispute Artifact",
      confidence: 0.96
    };
  }

  return {
    isRelevant: false,
    reason: "Unrecognized Document Type — Missing invoice or warranty clauses",
    confidence: 0.25
  };
}

async function handleMultipleFiles(fileList) {
  const statusEl = document.getElementById("upload-status");
  if (!statusEl) return;

  statusEl.classList.remove("hidden");
  statusEl.innerHTML = `
    <div class="flex items-center justify-center gap-2 text-cyan-300">
      <i data-lucide="loader-2" class="w-4 h-4 animate-spin"></i>
      <span>Uploading and running PyMuPDF & Structured Extraction on ${fileList.length} file(s)...</span>
    </div>
  `;
  if (window.lucide) lucide.createIcons();

  let relevantCount = 0;
  let irrelevantCount = 0;
  let newFactsCount = 0;

  for (const file of fileList) {
    try {
      const formData = new FormData();
      formData.append("file", file);

      const resp = await fetch(`/api/cases/${CurrentCase.caseId}/upload`, {
        method: "POST",
        body: formData,
      });

      if (!resp.ok) {
        throw new Error(`Upload failed with status ${resp.status}`);
      }

      const data = await resp.json();

      if (data.is_relevant === false) {
        irrelevantCount++;
        const auditFact = (data.facts && data.facts.length > 0) ? data.facts[0] : null;
        CurrentCase.facts.push({
          field: "document_audit",
          value: auditFact ? auditFact.value : `Non-dispute document: ${file.name}`,
          source: file.name,
          confidence: auditFact ? auditFact.confidence : 0.12,
          status: "unverified"
        });
      } else {
        relevantCount++;
        newFactsCount += (data.facts ? data.facts.length : 0);
      }

      if (data.all_facts && data.all_facts.length > 0) {
        CurrentCase.facts = data.all_facts;
      }
      if (data.canonical_facts && data.canonical_facts.length > 0) {
        CurrentCase.canonical_facts = data.canonical_facts;
      }
      if (data.conflicts !== undefined) {
        CurrentCase.conflicts = data.conflicts;
      }

      if (data.resolved_facts) {
        CurrentCase.resolved_facts = data.resolved_facts;
        if (data.resolved_facts.product_name) CurrentCase.product = data.resolved_facts.product_name;
        if (data.resolved_facts.seller_name) CurrentCase.seller = data.resolved_facts.seller_name;
        if (data.resolved_facts.purchase_date) CurrentCase.purchaseDate = data.resolved_facts.purchase_date;
        if (data.resolved_facts.warranty_period_months) CurrentCase.warrantyText = `${data.resolved_facts.warranty_period_months} Months`;
      } else {
        for (const fact of (data.facts || [])) {
          if (fact.field === "product_name" && fact.value) CurrentCase.product = fact.value;
          if (fact.field === "seller_name" && fact.value) CurrentCase.seller = fact.value;
          if (fact.field === "purchase_date" && fact.value) CurrentCase.purchaseDate = fact.value;
          if (fact.field === "warranty_period_months" && fact.value) CurrentCase.warrantyText = `${fact.value} Months`;
        }
      }

      CurrentCase.uploadedFiles = CurrentCase.uploadedFiles || [];
      if (!CurrentCase.uploadedFiles.some(f => (typeof f === 'string' ? f : f.name) === file.name)) {
        CurrentCase.uploadedFiles.push({ name: file.name, size: file.size });
      }
    } catch (err) {
      console.error("Upload error for file:", file.name, err);
      irrelevantCount++;
      CurrentCase.facts.push({
        field: "upload_warning",
        value: `Processing error for ${file.name}: ${err.message}`,
        source: file.name,
        confidence: 0.10,
        status: "unverified"
      });
    }
  }

  const fieldGroups = {};
  for (const f of CurrentCase.facts) {
    if (f.status === "conflicting") {
      fieldGroups[f.field] = fieldGroups[f.field] || [];
      if (!fieldGroups[f.field].some(o => o.value === f.value)) {
        fieldGroups[f.field].push({ value: f.value, source: f.source, confidence: f.confidence });
      }
    }
  }
  CurrentCase.conflicts = Object.keys(fieldGroups).map(field => ({
    field: field,
    options: fieldGroups[field]
  }));

  CurrentCase.filesCountText = `${CurrentCase.facts.filter(f => f.field !== 'document_audit').length} Verified Facts`;

  renderAll();

  if (irrelevantCount > 0 && relevantCount === 0) {
    statusEl.innerHTML = `
      <div class="flex flex-col items-center gap-1 text-amber-300">
        <div class="flex items-center gap-2">
          <i data-lucide="alert-triangle" class="w-4 h-4 text-amber-400"></i>
          <span><b>Intelligent Audit Flag:</b> Detected ${irrelevantCount} non-consumer file(s) (e.g. academic/lab PDF). PyMuPDF extracted text, found zero purchase/warranty terms. Recorded with <b>12% confidence (Unverified)</b>.</span>
        </div>
      </div>
    `;
  } else if (irrelevantCount > 0 && relevantCount > 0) {
    statusEl.innerHTML = `
      <div class="flex flex-col items-center gap-1 text-cyan-300">
        <div class="flex items-center gap-2">
          <i data-lucide="check-circle" class="w-4 h-4 text-emerald-400"></i>
          <span>Processed ${relevantCount} commercial evidence document(s) (${newFactsCount} facts extracted), and flagged ${irrelevantCount} non-dispute file(s).</span>
        </div>
      </div>
    `;
  } else {
    statusEl.innerHTML = `
      <div class="flex items-center justify-center gap-2 text-emerald-400">
        <i data-lucide="check-circle" class="w-4 h-4"></i>
        <span>Successfully extracted <b>${newFactsCount}</b> verified facts from <b>${relevantCount}</b> evidence document(s)! Fact Ledger updated.</span>
      </div>
    `;
  }

  if (window.lucide) lucide.createIcons();
}

function resetToBlankCase() {
  CurrentCase = JSON.parse(JSON.stringify(PredefinedCases.blank));
  CurrentCase.caseId = `CS-CUSTOM-${Math.floor(1000 + Math.random() * 9000)}`;
  CurrentCase.uploadedFiles = [];
  
  const sel = document.getElementById("case-switcher-select");
  if (sel) sel.value = "blank";

  const statusEl = document.getElementById("upload-status");
  if (statusEl) {
    statusEl.classList.remove("hidden");
    statusEl.innerHTML = `
      <div class="flex items-center justify-center gap-2 text-cyan-300">
        <i data-lucide="folder-plus" class="w-4 h-4"></i>
        <span><b>Clean Workspace Ready:</b> Fact Ledger and Timeline are cleared. Upload your own documents below!</span>
      </div>
    `;
  }

  renderAll();
}

function setupEventListeners() {
  const caseSelect = document.getElementById("case-switcher-select");
  if (caseSelect) {
    caseSelect.addEventListener("change", (e) => {
      const selected = e.target.value;
      if (PredefinedCases[selected]) {
        CurrentCase = JSON.parse(JSON.stringify(PredefinedCases[selected]));
        renderAll();
      }
    });
  }

  const btnReset = document.getElementById("btn-reset-blank");
  if (btnReset) {
    btnReset.addEventListener("click", () => {
      resetToBlankCase();
    });
  }

  document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
      document.querySelectorAll(".tab-pane").forEach(p => p.classList.add("hidden"));

      btn.classList.add("active");
      const target = btn.getAttribute("data-tab");
      const pane = document.getElementById(target);
      if (pane) pane.classList.remove("hidden");
    });
  });

  const btnAnalysis = document.getElementById("btn-run-analysis");
  if (btnAnalysis) {
    btnAnalysis.addEventListener("click", async () => {
      btnAnalysis.innerHTML = `<i data-lucide="loader-2" class="w-4 h-4 animate-spin"></i><span>Running Analysis Engine...</span>`;
      if (window.lucide) lucide.createIcons();

      try {
        const resp = await fetch(`/api/cases/${CurrentCase.caseId}/analyze`, {
          method: "POST"
        });

        if (resp.ok) {
          const report = await resp.json();
          CurrentCase.score = report.total_score || 0;

          if (report.score_breakdown && report.score_breakdown.length > 0) {
            CurrentCase.dimensions = report.score_breakdown.map(sb => ({
              name: sb.dimension,
              score: sb.actual_score,
              max: sb.max_score,
              color: sb.actual_score === sb.max_score ? "text-emerald-400" : (sb.actual_score > 0 ? "text-amber-400" : "text-rose-400")
            }));
          }

          if (report.evidence_checklist && report.evidence_checklist.length > 0) {
            CurrentCase.checklist = report.evidence_checklist.map(ec => ({
              name: ec.item_name,
              category: ec.required ? "Required Evidence" : "Optional / Supporting",
              file: ec.source_filename || "Missing in Ledger",
              status: ec.status === "found" ? "found" : (ec.status === "partial" ? "partial" : "missing")
            }));
          }

          if (report.rule_results && report.rule_results.length > 0) {
            CurrentCase.rules = report.rule_results.map(rr => {
              let badgeColor = "bg-rose-500/15 text-rose-300 border-rose-500/25";
              if (rr.rule_status === "PASSED") badgeColor = "bg-emerald-500/15 text-emerald-300 border-emerald-500/25";
              else if (rr.rule_status === "FAILED_PRECONDITION") badgeColor = "bg-amber-500/15 text-amber-300 border-amber-500/25";
              return {
                name: rr.rule_name.replace(/_/g, " ").toUpperCase(),
                status: rr.rule_status,
                badgeColor: badgeColor,
                text: rr.summary
              };
            });
          }

          if (report.draft_complaint) {
            CurrentCase.complaintDraft = report.draft_complaint;
          }

          if (report.timeline && report.timeline.length > 0) {
            CurrentCase.timeline = report.timeline.map(item => {
              let icon = "clock";
              const typeStr = (item.event_type || "").toLowerCase();
              if (typeStr.includes("purchase")) icon = "shopping-bag";
              else if (typeStr.includes("delivery")) icon = "truck";
              else if (typeStr.includes("defect")) icon = "alert-triangle";
              else if (typeStr.includes("complaint")) icon = "mail";
              else if (typeStr.includes("response") || typeStr.includes("denial") || typeStr.includes("rejection")) icon = "x-circle";

              let dateDisplay = item.event_date || "Date Unspecified";
              if (dateDisplay.includes("T")) dateDisplay = dateDisplay.split("T")[0];

              return {
                icon: icon,
                type: (item.event_type || "Chronological Event").replace(/_/g, " ").toUpperCase(),
                date: dateDisplay,
                desc: item.description,
                file: item.source_filename || "Document Evidence"
              };
            });
          }

          if (report.relevant_policies && report.relevant_policies.length > 0) {
            CurrentCase.policies = report.relevant_policies.map(p => ({
              title: p.citation || `${p.source_name} — ${p.section}`,
              tag: p.relevance || "Governing Statute",
              quote: p.excerpt || ""
            }));
          }

          if (report.resolved_facts) {
            CurrentCase.resolved_facts = report.resolved_facts;
            if (report.resolved_facts.product_name) CurrentCase.product = report.resolved_facts.product_name;
            if (report.resolved_facts.seller_name) CurrentCase.seller = report.resolved_facts.seller_name;
            if (report.resolved_facts.purchase_date) CurrentCase.purchaseDate = report.resolved_facts.purchase_date;
            if (report.resolved_facts.warranty_period_months) CurrentCase.warrantyText = `${report.resolved_facts.warranty_period_months} Months`;
          }

          renderAll();
        }
      } catch (e) {
        console.warn("Backend analysis fallback:", e);
      }

      btnAnalysis.innerHTML = `<i data-lucide="check" class="w-4 h-4"></i><span>Analysis Complete</span>`;
      if (window.lucide) lucide.createIcons();

      document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
      document.querySelectorAll(".tab-pane").forEach(p => p.classList.add("hidden"));
      const gapBtn = document.querySelector('[data-tab="tab-gap"]');
      const gapPane = document.getElementById("tab-gap");
      if (gapBtn) gapBtn.classList.add("active");
      if (gapPane) gapPane.classList.remove("hidden");
    });
  }

  const fileInput = document.getElementById("evidence-file-input");
  if (fileInput) {
    fileInput.addEventListener("change", (e) => {
      if (e.target.files && e.target.files.length > 0) {
        handleMultipleFiles(Array.from(e.target.files));
      }
    });
  }

  const dropzone = document.getElementById("upload-dropzone");
  if (dropzone) {
    ["dragenter", "dragover"].forEach(eventName => {
      dropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        dropzone.classList.add("border-cyan-400", "bg-cyan-500/5");
      }, false);
    });

    ["dragleave", "drop"].forEach(eventName => {
      dropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        dropzone.classList.remove("border-cyan-400", "bg-cyan-500/5");
      }, false);
    });

    dropzone.addEventListener("drop", (e) => {
      const dt = e.dataTransfer;
      if (dt.files && dt.files.length > 0) {
        handleMultipleFiles(Array.from(dt.files));
      }
    }, false);
  }

  const btnCopy = document.getElementById("btn-copy-draft");
  if (btnCopy) {
    btnCopy.addEventListener("click", () => {
      navigator.clipboard.writeText(CurrentCase.complaintDraft).then(() => {
        const text = document.getElementById("copy-btn-text");
        if (text) text.textContent = "Copied to Clipboard!";
        setTimeout(() => {
          if (text) text.textContent = "Copy Text";
        }, 2000);
      });
    });
  }

  const btnDownload = document.getElementById("btn-download-dossier");
  if (btnDownload) {
    btnDownload.addEventListener("click", () => {
      const blob = new Blob([CurrentCase.complaintDraft], { type: "text/plain;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${CurrentCase.caseId}_Consumer_Grievance_Dossier.txt`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    });
  }
}

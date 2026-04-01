# RangeGuard — Product Roadmap

## Vision

RangeGuard is a camera-based intelligence platform for golf driving ranges. One installation, three layers of value — each built on the same hardware and pipeline.

```
Layer 1: Revenue Protection    ← gets you in the door
Layer 2: Facility Intelligence ← makes you sticky
Layer 3: Customer Insights     ← makes you indispensable
```

---

## Layer 1: Revenue Protection (Current — MVP)

**Status**: Built and demo-ready

**What it does**: Detects and deters ball theft between the driving range and short game area using cross-camera person tracking.

**Features**:
- [x] Person detection and tracking (YOLOv8 + ByteTrack)
- [x] Cross-camera re-identification (OSNet / color histogram)
- [x] Zone-based movement tracking (polygon zone engine)
- [x] Theft pattern detection: Range → Short Game → Range
- [x] Reverse pattern detection: Short Game → Range (unpaid usage)
- [x] Real-time alert feed with severity levels
- [x] Revenue saved counter (R75/bucket)
- [x] Person movement timeline
- [x] Daily stats with hourly alert chart
- [x] Staff alert notifications (browser push + sound)
- [x] Acknowledge workflow for alert accountability
- [x] Demo mode for sales presentations

**Revenue model**: One-time setup fee + monthly subscription
**Pitch**: "You're losing R4,500+/month to ball theft. RangeGuard stops it for less than that."

---

## Layer 2: Facility Intelligence

**Status**: Planned — next phase after first paying customer
**Extra hardware needed**: None — uses existing cameras and pipeline

### 2a. Operational Analytics Dashboard

Real-time and historical facility insights the owner currently has to guess at.

- [ ] **Peak hour analysis** — which hours/days are busiest, visualised as heatmaps
- [ ] **Session duration tracking** — how long customers actually stay per visit
- [ ] **Bay utilisation** — which hitting bays are most/least used
- [ ] **Zone flow patterns** — how people move through the facility
- [ ] **Daily/weekly/monthly trend reports** — exportable for business planning
- [ ] **Comparison views** — this week vs last week, this month vs last month

**Owner value**: Data-driven staffing decisions, targeted off-peak promotions, understand actual capacity usage.

### 2b. Smart Staffing

- [ ] **Real-time staffing suggestions** — "Range is 90% full, Short Game is empty — move staff to range"
- [ ] **Ball picker optimisation** — track where balls land most frequently, optimise collection routes
- [ ] **Predicted busy periods** — based on historical patterns, forecast tomorrow's demand

**Owner value**: Do more with the same staff. Stop overstaffing quiet periods and understaffing busy ones.

### 2c. Safety & Security

No new models — just new rules on the existing detection pipeline.

- [ ] **After-hours intrusion detection** — motion alerts when range is closed
- [ ] **Incident auto-recording** — save 30-second clips when any alert fires
- [ ] **Equipment area monitoring** — alert if someone enters restricted areas
- [ ] **Emergency detection** — person down/motionless for extended period

**Owner value**: Replaces or augments a security guard. 24/7 coverage with zero fatigue.

---

## Layer 3: Customer Insights

**Status**: Future — builds on months of tracking data
**Extra hardware needed**: None

### 3a. Customer Intelligence

- [ ] **Repeat visitor detection** — Re-ID recognises regulars across days/weeks
- [ ] **Visit frequency reports** — "Your top 20 customers visited X times this month"
- [ ] **Churn detection** — regular customer hasn't visited in 2+ weeks → trigger outreach
- [ ] **Customer segmentation** — group by visit frequency, session duration, preferred zone
- [ ] **Conversion tracking** — short game → range crossover (legitimate paid transitions)

**Owner value**: Understand who your best customers are. Know when you're losing them before they're gone.

### 3b. Revenue Optimisation

- [ ] **Dynamic pricing signals** — data to support peak/off-peak pricing decisions
- [ ] **Upsell triggers** — "Customer has been at range for 45 min" → suggest short game add-on
- [ ] **Bay availability display** — customer-facing screen showing open bays and estimated wait
- [ ] **Membership value analysis** — which membership tiers are most/least profitable

**Owner value**: Make more per customer without adding services.

### 3c. Pro Shop Intelligence

- [ ] **Equipment usage inference** — which bays/zones see most activity (proxy for club type used)
- [ ] **Rental equipment tracking** — which rental clubs go out most, which sit idle
- [ ] **Purchase intent signals** — frequent visitors who don't own equipment → sales opportunity

**Owner value**: Stock what sells. Know who to pitch to.

---

## Explicitly NOT on the Roadmap

These are adjacent opportunities but different products. Don't dilute focus.

| Idea | Why Not (for now) |
|------|-------------------|
| **Swing analysis / skill assessment** | Different CV domain (pose estimation, biomechanics). Companies like Sportsbox AI are funded specifically for this. Potential future partnership, not build. |
| **Lesson/instructor management** | This is a scheduling/CRM problem, not a CV problem. Existing golf software (Lightspeed, foreUP) handles this. |
| **Energy management (lighting, irrigation)** | IoT integration play, not CV. Different buyer, different sale. Consider as a Layer 4 partner integration if occupancy data is valuable to their system. |
| **Ball tracking (where each ball lands)** | Requires high-speed cameras and specialised CV. Different hardware, different price point. TrackMan and TopTracer own this space. |

---

## Scaling Strategy

### Phase 1: Prove (Now → First Customer)
- Deploy at one range
- Prove ROI with real theft prevention numbers
- Collect 3 months of data for Layer 2 analytics

### Phase 2: Package (Customer 1 → Customers 2-5)
- Standardise installation process (< 1 day setup)
- Build installer toolkit (auto camera discovery, zone drawing UI)
- Create tiered pricing:
  - **RangeGuard Protect** — Layer 1 only (revenue protection)
  - **RangeGuard Pro** — Layers 1 + 2 (protection + facility intelligence)
  - **RangeGuard Enterprise** — All layers + custom integrations

### Phase 3: Scale (5+ Customers)
- Multi-site dashboard (owner manages multiple ranges from one view)
- Cloud processing option (vs. edge-only)
- API for third-party integrations (POS systems, booking platforms)
- Reseller/installer partnerships

### Market Size (South Africa)
- ~200+ driving ranges nationally
- Average range revenue: R50k-R150k/month
- RangeGuard at 5-10% of revenue = R2,500-R15,000/month per site
- Total addressable: R6M-R36M/year nationally
- Scale to other countries with driving range culture (UK, US, Australia, Japan, Korea)

---

## Technical Foundation

Everything above runs on the same core pipeline:

```
Cameras (existing) → YOLOv8 Detection → ByteTrack Tracking → OSNet Re-ID
                                    ↓
                            Zone Engine → Rule Engine → Alerts
                                    ↓
                        FastAPI Backend → Dashboard / API
```

New features = new rules + new dashboard views. Same cameras, same compute, same codebase. That's the leverage.

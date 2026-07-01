// Mock data for the DreamWork dashboard prototype.
//
// This mirrors the REAL domain model in dreamwork/core/domain.py so the prototype is a faithful
// visual reference, not a divergent toy:
//   - Firm          — the investor firm (fund-level record)
//   - Partner       — a person at a firm (relationships live here)
//   - Round         — the raise you're running
//   - PipelineEntry — an investor's state in a round, with two INDEPENDENT axes:
//        stage   (progression): sourced → intro_requested → contacted → meeting →
//                 in_conversation → diligence → committed → closed
//        outcome (live status):  active | snoozed | passed | next_round
//     (see docs/pipeline.md — passed/next_round are kept, never deleted)
//   - is_lead, ticket_estimate_usd, first/last_contact_date, next_step, snooze_until on the entry.
//
// The normalized entities below are the source of truth; `investors` is an explicit JOIN
// (PipelineEntry ⋈ Firm ⋈ Partner) — exactly what the real dashboard reads. Views consume the
// join. `direction`, `peerIds`, `introducedBy` are prototype-only display extras, not core fields.
//
// Swap DW_DATA for a real API/MCP layer later; keep the same entity shapes.

const DW_DATA = (() => {
  // The raise you're running (core: Round).
  const round = {
    id: "r1", company: "Uplift360", label: "Seed",
    targetRaise: 2500000, raisedSoFar: 1000000,
    founder: { name: "Jamie Rowick", role: "Founder & CEO", initials: "JR" },
  };

  // Peer founders in the Extantia-style closed network — used for warm-intro overlap.
  const peers = [
    { id: "p1", name: "Alicia Chen", company: "Fernwell", initials: "AC" },
    { id: "p2", name: "Marcus Boyd", company: "Loopstack", initials: "MB" },
    { id: "p3", name: "Priya Nair", company: "Verdant Labs", initials: "PN" },
    { id: "p4", name: "Theo Kastanis", company: "Ridgeline", initials: "TK" },
    { id: "p5", name: "Sena Okoye", company: "Bramblewood", initials: "SO" },
    { id: "p6", name: "Dan Petrov", company: "Kindling AI", initials: "DP" },
    { id: "p7", name: "Wren Iyer", company: "Northbound", initials: "WI" },
  ];

  // Compact seed rows grouped by destination entity. Each becomes a Firm + Partner + PipelineEntry.
  //   stage/outcome are canonical (see above); isLead = potential lead for THIS round.
  //   ticketEst = ticket_estimate_usd; ticket = firm's typical [min, max] check.
  const seed = [
    { fid: "f_bluepeak", firm: "Bluepeak Ventures", type: "VC", loc: "San Francisco, CA", sectors: ["Fintech", "B2B SaaS"], ticket: [250000, 1000000], leads: true, follows_on: true,
      person: "Grace Whitfield", role: "General Partner", initials: "GW", color: "#6ee7b7",
      stage: "committed", outcome: "active", isLead: true, ticketEst: 700000, first: "2026-06-05", last: "2026-06-27",
      direction: "inbound", introducedBy: null, peerIds: ["p1", "p6"], nextStep: "Counter-sign term sheet",
      notes: "Reached out after seeing our Demo Day pitch. Moving fast, wants to lead." },
    { fid: "f_anchorpoint", firm: "Anchorpoint Capital", type: "VC", loc: "New York, NY", sectors: ["B2B SaaS", "Marketplaces"], ticket: [100000, 500000], leads: false,
      person: "Marcus Lin", role: "Partner", initials: "ML", color: "#93c5fd",
      stage: "diligence", outcome: "active", isLead: false, ticketEst: 300000, first: "2026-06-08", last: "2026-06-25",
      direction: "outbound", introducedBy: "Theo Kastanis (Ridgeline)", peerIds: ["p4"], nextStep: "Send cohort retention data",
      notes: "Second partner meeting done. Requested cohort retention data." },
    { fid: "f_meridian", firm: "Meridian Fund", type: "VC", loc: "Austin, TX", sectors: ["Fintech"], ticket: [50000, 300000], leads: false,
      person: "Sofia Reyes", role: "Principal", initials: "SR", color: "#fca5a5",
      stage: "meeting", outcome: "active", isLead: false, ticketEst: 175000, first: "2026-06-20", last: "2026-06-24",
      direction: "outbound", introducedBy: null, peerIds: ["p3", "p5"], nextStep: "First call Tue",
      notes: "Cold outbound via warm LinkedIn message. First call booked for next week." },
    { fid: "f_harborlight", firm: "Harborlight Partners", type: "VC", loc: "Chicago, IL", sectors: ["Fintech", "Infra"], ticket: [500000, 2000000], leads: true, follows_on: true,
      person: "David Okonkwo", role: "Managing Partner", initials: "DO", color: "#fcd34d",
      stage: "closed", outcome: "active", isLead: true, ticketEst: 500000, first: "2026-05-20", last: "2026-06-10",
      direction: "inbound", introducedBy: "Alicia Chen (Fernwell)", peerIds: ["p1", "p2"], nextStep: null,
      notes: "Wired $500k as part of the round. Great follow-on potential for A." },
    { fid: "f_cascade", firm: "Cascade Angels", type: "Angel", loc: "Seattle, WA", sectors: ["B2B SaaS"], ticket: [25000, 100000], leads: false,
      person: "Elena Petrov", role: "Angel", initials: "EP", color: "#a5b4fc",
      stage: "closed", outcome: "active", isLead: false, ticketEst: 75000, first: "2026-05-25", last: "2026-06-05",
      direction: "outbound", introducedBy: null, peerIds: ["p6"], nextStep: null,
      notes: "Fast angel check, wired in 4 days. Very responsive, great operator background." },
    { fid: "f_northstar", firm: "Northstar Seed", type: "VC", loc: "Boston, MA", sectors: ["Marketplaces", "B2B SaaS"], ticket: [150000, 750000], leads: false,
      person: "Ben Carruthers", role: "Partner", initials: "BC", color: "#67e8f9",
      stage: "contacted", outcome: "passed", isLead: false, ticketEst: null, first: "2026-05-20", last: "2026-05-28",
      direction: "outbound", introducedBy: null, peerIds: ["p2", "p7"], nextStep: null,
      notes: "Passed — too early for their thesis, said to circle back at $1M ARR." },
    { fid: "f_originrow", firm: "Origin Row Capital", type: "VC", loc: "Los Angeles, CA", sectors: ["Fintech"], ticket: [300000, 1200000], leads: true,
      person: "Nadia Farouk", role: "Partner", initials: "NF", color: "#f9a8d4",
      stage: "diligence", outcome: "active", isLead: true, ticketEst: 600000, first: "2026-06-10", last: "2026-06-26",
      direction: "inbound", introducedBy: "Sena Okoye (Bramblewood)", peerIds: ["p5"], nextStep: "Answer data-room legal Qs",
      notes: "Inbound via portfolio founder intro. Legal reviewing our data room now." },
    { fid: "f_fieldstone", firm: "Fieldstone Ventures", type: "VC", loc: "Denver, CO", sectors: ["Infra", "B2B SaaS"], ticket: [1000000, 3000000], leads: true,
      person: "Owen Marsh", role: "Partner", initials: "OM", color: "#c4b5fd",
      stage: "contacted", outcome: "next_round", isLead: false, ticketEst: null, first: "2026-06-02", last: "2026-06-02",
      direction: "outbound", introducedBy: null, peerIds: [], nextStep: "Re-approach at Series A",
      notes: "Too early for their check size — flagged as a Series A target." },
    { fid: "f_ridgeback", firm: "Ridgeback Capital", type: "VC", loc: "San Francisco, CA", sectors: ["B2B SaaS"], ticket: [200000, 600000], leads: false,
      person: "Chloe Bergman", role: "Principal", initials: "CB", color: "#6ee7b7",
      stage: "meeting", outcome: "active", isLead: false, ticketEst: 400000, first: "2026-06-19", last: "2026-06-24",
      direction: "outbound", introducedBy: "Dan Petrov (Kindling AI)", peerIds: ["p6", "p4"], nextStep: "Prep first call",
      notes: "First call scheduled via warm intro. She backed two of our peers already." },
    { fid: "f_cobblestone", firm: "Cobblestone Angels", type: "Angel", loc: "Miami, FL", sectors: ["Fintech", "Marketplaces"], ticket: [10000, 50000], leads: false,
      person: "Isaiah Thompson", role: "Angel", initials: "IT", color: "#fdba74",
      stage: "contacted", outcome: "active", isLead: false, ticketEst: 30000, first: "2026-06-20", last: "2026-06-20",
      direction: "inbound", introducedBy: null, peerIds: [], nextStep: "Reply with deck",
      notes: "DM'd us on X after our launch thread. Waiting on our reply with deck." },
    { fid: "f_tidewater", firm: "Tidewater Fund", type: "VC", loc: "San Francisco, CA", sectors: ["Fintech", "B2B SaaS"], ticket: [400000, 1500000], leads: true,
      person: "Rachel Kim", role: "General Partner", initials: "RK", color: "#93c5fd",
      stage: "committed", outcome: "active", isLead: true, ticketEst: 750000, first: "2026-06-01", last: "2026-06-28",
      direction: "outbound", introducedBy: "Priya Nair (Verdant Labs)", peerIds: ["p3", "p1"], nextStep: "Legal review of term sheet",
      notes: "Term sheet in hand, $750k at same terms as Bluepeak. Reviewing with counsel." },
    { fid: "f_ferrystreet", firm: "Ferry Street Capital", type: "VC", loc: "Atlanta, GA", sectors: ["Marketplaces"], ticket: [100000, 400000], leads: false,
      person: "Malik Johnson", role: "Partner", initials: "MJ", color: "#fca5a5",
      stage: "contacted", outcome: "passed", isLead: false, ticketEst: null, first: "2026-05-10", last: "2026-05-15",
      direction: "outbound", introducedBy: null, peerIds: ["p7"], nextStep: null,
      notes: "Passed on sector fit — they've gone all-in on vertical marketplaces only." },
    { fid: "f_lighthouse", firm: "Lighthouse Angels", type: "Angel", loc: "Portland, OR", sectors: ["B2B SaaS"], ticket: [15000, 75000], leads: false,
      person: "Hana Suzuki", role: "Angel", initials: "HS", color: "#fcd34d",
      stage: "closed", outcome: "active", isLead: false, ticketEst: 25000, first: "2026-05-24", last: "2026-05-30",
      direction: "inbound", introducedBy: "Wren Iyer (Northbound)", peerIds: ["p7"], nextStep: null,
      notes: "Wired $25k same week as the call. Offered to make 3 more intros." },
    { fid: "f_cormorant", firm: "Cormorant Partners", type: "VC", loc: "New York, NY", sectors: ["Infra"], ticket: [1500000, 4000000], leads: true,
      person: "Victor Andrade", role: "Partner", initials: "VA", color: "#a5b4fc",
      stage: "contacted", outcome: "next_round", isLead: false, ticketEst: null, first: "2026-06-01", last: "2026-06-01",
      direction: "outbound", introducedBy: null, peerIds: [], nextStep: "Re-approach at $1.5M ARR",
      notes: "Too early — flagged as an A-round target once we hit $1.5M ARR." },
    { fid: "f_sableoak", firm: "Sable Oak Capital", type: "VC", loc: "Chicago, IL", sectors: ["Fintech"], ticket: [250000, 900000], leads: false,
      person: "Laila Haddad", role: "Principal", initials: "LH", color: "#67e8f9",
      stage: "meeting", outcome: "active", isLead: false, ticketEst: 500000, first: "2026-06-22", last: "2026-06-26",
      direction: "inbound", introducedBy: null, peerIds: ["p5", "p3"], nextStep: "Intro call next week",
      notes: "Inbound after her associate sourced us from a fintech newsletter roundup." },
    { fid: "f_millbrook", firm: "Millbrook Ventures", type: "VC", loc: "Boston, MA", sectors: ["B2B SaaS", "Infra"], ticket: [300000, 1000000], leads: false,
      person: "Corey Blackwood", role: "Partner", initials: "CO", color: "#f9a8d4",
      stage: "diligence", outcome: "active", isLead: false, ticketEst: 500000, first: "2026-06-12", last: "2026-06-24",
      direction: "outbound", introducedBy: "Marcus Boyd (Loopstack)", peerIds: ["p2"], nextStep: "Provide design-partner refs",
      notes: "Reference calls in progress — checking with two of our design partners." },
    { fid: "f_solstice", firm: "Solstice Angels Syndicate", type: "Angel", loc: "Washington, DC", sectors: ["Fintech", "B2B SaaS"], ticket: [20000, 150000], leads: false,
      person: "Amara Osei", role: "Syndicate Lead", initials: "AO", color: "#c4b5fd",
      stage: "contacted", outcome: "active", isLead: false, ticketEst: 80000, first: "2026-06-19", last: "2026-06-19",
      direction: "inbound", introducedBy: null, peerIds: ["p1"], nextStep: "Send deck this week",
      notes: "Syndicate lead reached out post-podcast appearance. Sending deck this week." },
    { fid: "f_wraithpeak", firm: "Wraith Peak Capital", type: "VC", loc: "San Francisco, CA", sectors: ["Marketplaces", "Fintech"], ticket: [150000, 600000], leads: false,
      person: "Felix Granger", role: "Partner", initials: "FG", color: "#fdba74",
      stage: "contacted", outcome: "snoozed", isLead: false, ticketEst: null, first: "2026-06-18", last: "2026-06-18", snoozeUntil: "2026-07-15",
      direction: "outbound", introducedBy: null, peerIds: [], nextStep: "Follow up after snooze",
      notes: "Sent cold outbound referencing Rachel Kim. Snoozed until mid-July to give it air." },
    { fid: "f_rowanhill", firm: "Rowan Hill Capital", type: "Corporate VC", loc: "San Francisco, CA", sectors: ["Fintech"], ticket: [750000, 2500000], leads: true,
      person: "Simone Delacroix", role: "Investment Director", initials: "SD", color: "#6ee7b7",
      stage: "meeting", outcome: "active", isLead: false, ticketEst: 1000000, first: "2026-06-22", last: "2026-06-22",
      direction: "inbound", introducedBy: null, peerIds: ["p4", "p6"], nextStep: "Partnership + investment call",
      notes: "Strategic arm reached out about a potential partnership + investment combo." },
    { fid: "f_ember", firm: "Ember & Co", type: "Family Office", loc: "Palm Beach, FL", sectors: ["Fintech", "B2B SaaS"], ticket: [500000, 1500000], leads: true,
      person: "Julian Voss", role: "Principal", initials: "JV", color: "#93c5fd",
      stage: "closed", outcome: "active", isLead: false, ticketEst: 400000, first: "2026-06-01", last: "2026-06-15",
      direction: "outbound", introducedBy: "Alicia Chen (Fernwell)", peerIds: ["p1"], nextStep: null,
      notes: "Closed $400k. Family office likes to move quietly but reliably." },
  ];

  // --- Build normalized entities from the seed ---
  const firms = seed.map((s) => ({
    id: s.fid, name: s.firm, type: s.type,
    geographies: [s.loc], sectors: s.sectors,
    ticket_size_usd_range: s.ticket, leads: !!s.leads, follows_on: !!s.follows_on,
    // peer companies that also know this firm — prototype stand-in for the shared network.
    extantia_portfolio_overlap: s.peerIds.map((pid) => (peers.find((p) => p.id === pid) || {}).company).filter(Boolean),
  }));

  const partners = seed.map((s, idx) => ({
    id: "pt" + (idx + 1), firm_id: s.fid, name: s.person, role: s.role,
  }));

  const pipeline = seed.map((s, idx) => ({
    id: "pe" + (idx + 1), round_id: round.id, firm_id: s.fid, partner_id: "pt" + (idx + 1),
    stage: s.stage, outcome: s.outcome, is_lead: s.isLead,
    ticket_estimate_usd: s.ticketEst,
    first_contact_date: s.first, last_contact_date: s.last,
    next_step: s.nextStep || null, snooze_until: s.snoozeUntil || null,
  }));

  // The JOIN the views read: PipelineEntry ⋈ Firm ⋈ Partner, materialized once so in-prototype
  // edits (drag-drop, detail updates) persist. Canonical fields + a few display-only extras.
  const investors = pipeline.map((entry, idx) => {
    const s = seed[idx];
    const firm = firms[idx];
    const partner = partners[idx];
    return {
      id: entry.id, entryId: entry.id, firmId: firm.id, partnerId: partner.id,
      // canonical, editable state
      stage: entry.stage, outcome: entry.outcome, isLead: entry.is_lead,
      ticketEstimateUsd: entry.ticket_estimate_usd,
      firstContact: entry.first_contact_date, lastActivity: entry.last_contact_date,
      nextStep: entry.next_step, snoozeUntil: entry.snooze_until,
      // joined display fields
      name: partner.name, role: partner.role, firm: firm.name, type: firm.type,
      ticketRange: firm.ticket_size_usd_range, sectors: firm.sectors, location: firm.geographies[0],
      stageFocus: [round.label], leads: firm.leads,
      initials: s.initials, color: s.color,
      // prototype-only extras (not core domain fields)
      direction: s.direction, introducedBy: s.introducedBy, peerIds: s.peerIds, notes: s.notes,
    };
  });

  // Chronological activity log across the whole network.
  const byPerson = (name) => (investors.find((i) => i.name === name) || {}).id;
  const activity = [
    { id: "a1", date: "2026-06-28", type: "committed", investorId: byPerson("Rachel Kim"), text: "Received signed term sheet from Rachel Kim at Tidewater Fund — $750k." },
    { id: "a2", date: "2026-06-27", type: "meeting", investorId: byPerson("Grace Whitfield"), text: "Partner meeting with Bluepeak Ventures — verbal commitment to lead the round." },
    { id: "a3", date: "2026-06-26", type: "inbound", investorId: byPerson("Nadia Farouk"), text: "Origin Row Capital sent data room follow-up questions." },
    { id: "a4", date: "2026-06-26", type: "inbound", investorId: byPerson("Laila Haddad"), text: "Laila Haddad (Sable Oak) booked an intro call for next Tuesday." },
    { id: "a5", date: "2026-06-25", type: "outbound", investorId: byPerson("Marcus Lin"), text: "Sent cohort retention data to Anchorpoint Capital for diligence." },
    { id: "a6", date: "2026-06-24", type: "meeting", investorId: byPerson("Chloe Bergman"), text: "First call with Chloe Bergman (Ridgeback Capital) via Dan Petrov intro." },
    { id: "a7", date: "2026-06-24", type: "outbound", investorId: byPerson("Corey Blackwood"), text: "Kicked off reference calls for Millbrook Ventures diligence." },
    { id: "a8", date: "2026-06-23", type: "meeting", investorId: byPerson("Sofia Reyes"), text: "Booked first call with Sofia Reyes at Meridian Fund." },
    { id: "a9", date: "2026-06-22", type: "inbound", investorId: byPerson("Simone Delacroix"), text: "Rowan Hill Capital (corporate VC) proposed a partnership + investment call." },
    { id: "a10", date: "2026-06-20", type: "inbound", investorId: byPerson("Isaiah Thompson"), text: "Isaiah Thompson DM'd asking for the deck after our launch thread." },
    { id: "a11", date: "2026-06-19", type: "inbound", investorId: byPerson("Amara Osei"), text: "Amara Osei's syndicate reached out after the fintech podcast episode." },
    { id: "a12", date: "2026-06-18", type: "outbound", investorId: byPerson("Felix Granger"), text: "Sent cold outbound to Felix Granger referencing Rachel Kim connection." },
    { id: "a13", date: "2026-06-15", type: "closed_won", investorId: byPerson("Julian Voss"), text: "Closed $400k from Julian Voss / Ember & Co." },
    { id: "a14", date: "2026-06-10", type: "closed_won", investorId: byPerson("David Okonkwo"), text: "Closed $500k from David Okonkwo / Harborlight Partners." },
    { id: "a15", date: "2026-06-05", type: "closed_won", investorId: byPerson("Elena Petrov"), text: "Closed $75k angel check from Elena Petrov." },
    { id: "a16", date: "2026-05-30", type: "closed_won", investorId: byPerson("Hana Suzuki"), text: "Closed $25k from Hana Suzuki, plus 3 offered intros." },
    { id: "a17", date: "2026-05-28", type: "passed", investorId: byPerson("Ben Carruthers"), text: "Ben Carruthers (Northstar Seed) passed — too early for thesis." },
    { id: "a18", date: "2026-05-15", type: "passed", investorId: byPerson("Malik Johnson"), text: "Malik Johnson (Ferry Street) passed — sector fit mismatch." },
    { id: "a19", date: "2026-06-02", type: "outbound", investorId: byPerson("Owen Marsh"), text: "Flagged Owen Marsh (Fieldstone) as a Series A target — too early now." },
    { id: "a20", date: "2026-06-01", type: "outbound", investorId: byPerson("Victor Andrade"), text: "Initial outreach to Victor Andrade at Cormorant Partners." },
  ];

  // Backwards-friendly alias so header code can read founder/target as before.
  const founder = {
    name: round.founder.name, company: round.company, role: round.founder.role,
    initials: round.founder.initials, round: round.label,
    targetRaise: round.targetRaise, raisedSoFar: round.raisedSoFar,
  };

  return { round, founder, peers, firms, partners, pipeline, investors, activity };
})();

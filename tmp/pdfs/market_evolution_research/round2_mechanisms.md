# Round 2 Cross-Examination: Mechanism Design and Market Formation

## Scope and epistemic status

This memo asks a narrow question: when does AI-agent activity become a genuine market, and when is it only a hierarchy, platform, procurement network, directory, or internal allocation system described with market language?

The analysis is intentionally non-prescriptive. It offers no product, company, financing, or investment direction. It separates three kinds of statements:

- Facts are attributed to dated primary or authoritative sources.
- Inferences are mechanism-design conclusions derived from specified institutional conditions.
- Speculation appears only in the forward evolution and opposite-world reconstructions.

The central conclusion is that increasing agent activity is neither necessary nor sufficient evidence of market formation. A million internal routing decisions can occur without one market transaction. A single competitive tender among independent legal principals can be a real, if thin, market. The decisive variables are not autonomy, message volume, or protocol adoption. They are the identity of the residual claimants, the scarcity and transferability of the object, the allocation rule, authority to bind, liability, payment, settlement, default, remedies, entry, and the ability to switch or bypass an intermediary.

## 1. The formation test

A candidate institution passes the market-formation test only when all of the following questions have concrete answers.

1. **Independent principals.** Are buyer and seller independent economic principals that retain gains and losses, or are they divisions, agents, or services controlled by one firm?
2. **Demand.** Who values the deliverable, controls a real budget, and can decline to buy?
3. **Supply.** Which independent counterparties can supply substitutes, and is entry commercially credible rather than merely technically possible?
4. **Inventory.** What scarce unit can be reserved or delivered: a call, task, outcome, license, capacity block, time slot, data right, or risk limit?
5. **Executable allocation.** Is there a posted offer, quote, negotiation, tender, auction, or other rule that binds allocation? A scheduler score is not a bid.
6. **Eligibility.** How are identity, authority, competence, solvency, sanctions, licensing, permissions, and conflicts established?
7. **Verification.** How are delivery, quality, provenance, constraint compliance, and counterfactual value established?
8. **Liability.** Which legal person bears losses for non-performance, infringement, data harm, fraud, or unsafe action?
9. **Payment.** What consideration moves, under whose mandate, through which rail?
10. **Settlement.** When are delivery and payment final? Can one become final without the other?
11. **Liquidity.** What are actual depth, fill rate, bid response, spread, slippage, repeat volume, and time to match? Liquidity cannot be inferred from listings or traffic.
12. **Reputation.** Is performance history attributable, task-conditioned, portable, and resistant to Sybil identities, selective reporting, and wash activity?
13. **Default.** What happens if the buyer, seller, verifier, insurer, platform, or clearing member fails?
14. **Disputes.** What evidence, neutral adjudicator, appeal path, and remedy apply?
15. **Contestability.** Can participants multi-home, switch, and bypass the intermediary while taking their identity, data, and reputation with them?

The test does not require a continuous order book. Posted-price retail, bilateral contracting, and an episodic reverse auction can each be a market. It does require exchange among independent principals and an executable transaction institution. A directory can help a future market form but is not one. A clearinghouse can support markets but cannot manufacture an underlying market where there are no competing executable orders.

The adverse-selection foundation comes from Akerlof's 1970 analysis of quality uncertainty. The moral-hazard and observability problem follows Holmstrom's 1979 analysis. Auction rules must be treated as incentive systems, not neutral plumbing, as shown by Myerson's 1981 auction-design work and Milgrom and Weber's 1982 model of information and bidding ([Akerlof, 1 August 1970](https://academic.oup.com/qje/article-abstract/84/3/488/1896241), [Holmstrom, 1979](https://doi.org/10.2307/3003320), [Myerson, 1 February 1981](https://pubsonline.informs.org/doi/10.1287/moor.6.1.58), [Milgrom and Weber, September 1982](https://doi.org/10.2307/1911865)).

## 2. Applied stage test

| Stage | Principals and object | Allocation, contract, and settlement | Liquidity | Formation verdict |
|---|---|---|---|---|
| 0. Single-agent automation | One enterprise allocates its own work to an internal agent | Managerial instruction; payroll, subscription, or cloud invoice | Not applicable | Hierarchy, not market |
| 1. Adaptive internal control plane | One enterprise routes steps among internal agents, models, tools, and verifiers | Scheduler or policy score; upstream vendors already contracted | Not applicable | Internal dispatch, not market |
| 2. Bundled agent platform | Customer buys one platform outcome; platform privately assembles suppliers | Subscription or negotiated platform contract; separate upstream contracts | Usage is not two-sided depth | Product firm and supply chain, not marketplace |
| 3. Directory and protocol discovery | Independent providers publish capabilities; buyers browse or agents discover | No binding offer, delivery contract, or integrated settlement | Listings are not liquidity | Directory or network, not market |
| 4. Approved procurement network | Enterprise buyer and independent approved suppliers exchange project or capacity commitments | RFQ, RFP, quote, negotiated contract, invoice settlement | Thin and episodic | Genuine procurement market when multiple suppliers compete |
| 5. Reverse auction | One buyer and several qualified independent suppliers compete for a standardized lot | Iterative or sealed descending bids, award, delivery acceptance, payment | One event can be a market without being liquid | Genuine market if specifications, independence, and host neutrality hold |
| 6. Spot API or task exchange | Independent buyers and sellers trade callable capacity, tools, data, or bounded tasks | Executable posted prices or bid-offer matching; metering, escrow, gross or net settlement | Must be measured by fills, depth, spread, and repeat volume | Genuine administered market if delivery and money settle |
| 7. Specialist outcome contracting | Buyer and legal operator trade heterogeneous project outcomes | Quote plus milestones, escrow, acceptance, holdback, remedies | Fragmented and thin | Genuine services market, not necessarily machine-autonomous |
| 8. Assurance and risk transfer | Enterprises or platforms buy verification, warranties, or coverage from independent firms | Audit contract, premium, policy limit, claims process, reserve-backed settlement | Bespoke and capital-constrained | Separate assurance or insurance market if independent and solvent |
| 9. Federated clearing | Existing venues and members submit obligations to a clearing layer | Rulebook, collateral, netting, delivery-versus-payment, finality, default waterfall | Consolidates only real underlying orders | Infrastructure, not a market by itself |

### Stage 0 to stage 1: automation becomes dispatch

The causal sequence begins with a human principal assigning work to an agent. A control plane then decomposes work into planning, retrieval, reasoning, generation, validation, repair, and escalation. It assigns models, tools, context, compute, and verification policies to each step. This can be economically valuable because it substitutes a portfolio policy for one static model.

Nothing in this sequence creates a market. Demand and supply remain under one residual claimant. The inventory is internal compute and attention. The allocation rule is a policy score rather than a bid. Payment is payroll, cloud billing, or internal transfer pricing. Failure is handled through retry or escalation rather than counterparty default. The right comparison is make-versus-buy and centralized versus decentralized control, not market versus no market.

An internal chargeback does not change the result if the enterprise can administratively rewrite the price, mandate the supplier, absorb every loss, and prevent external entry. It is a shadow price used for management. It becomes market-facing only when an authorized buyer agent can reject internal supply and contract with an independent seller under enforceable terms.

### Stage 1 to stage 2: dispatch becomes a bundled platform

The platform can combine frontier models, open models, clouds, specialist tools, verifiers, and humans. The customer receives one contract and one outcome surface. The platform buys or licenses the inputs and may switch them without the customer's involvement.

This is vertical production. The platform is a reseller, systems integrator, or product firm. It can create upstream procurement demand, but the customer is not participating in a market among the component suppliers. The platform owns the allocation rule, sees private supplier data, sets the retail price, and normally bears or disclaims the customer-facing obligation. High usage can coexist with zero two-sided liquidity.

The distinction matters because a platform can have strong bargaining power without operating a marketplace. It may use suppliers as inputs, acquire successful specialists, reserve favored latency for its own services, and hide routing rebates. Market language can obscure the fact that the customer's choice is only whether to buy the bundle.

### Stage 2 to stage 3: interoperability becomes discovery

Protocols reduce the cost of describing capabilities, delegating tasks, authenticating actors, and conveying authority. A2A's April 2025 design includes Agent Cards, task lifecycles, artifacts, and messages. The Linux Foundation became its neutral home in June 2025 ([Google A2A, 9 April 2025](https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/), [Linux Foundation, 23 June 2025](https://www.linuxfoundation.org/press/linux-foundation-launches-the-agent2agent-protocol-project-to-enable-secure-intelligent-communication-between-ai-agents)).

MCP's 18 June 2025 authorization specification binds access tokens to intended resources and forbids token passthrough, addressing confused-deputy risk. IETF RFC 8693, published in January 2020, distinguishes delegation from impersonation and supports actor chains while leaving the trust model and local policy out of scope. W3C Verifiable Credentials 2.0 became a Recommendation on 15 May 2025 and supports cryptographically verifiable claims among issuers, holders, and verifiers ([MCP authorization, 18 June 2025](https://modelcontextprotocol.io/specification/2025-06-18/basic/authorization), [RFC 8693](https://datatracker.ietf.org/doc/rfc8693/), [W3C VC 2.0 history](https://www.w3.org/standards/history/vc-data-model/)).

These facts lower coordination costs. They do not create a price, contract, liability allocation, settlement rule, or remedy. An Agent Card is closer to a machine-readable business card than an executable ask. A credential proves that an issuer made a claim; it does not prove that the holder is solvent, licensed for the transaction, legally bound, or capable of satisfying a judgment. Discovery becomes a market only after offers, authority, delivery, payment, and disputes are integrated.

### Stage 3 to stage 4: discovery becomes procurement

The first plausible market transition occurs when an enterprise buyer agent has a funded mandate and can issue a structured RFQ to several independent suppliers. The buyer specifies the task, security boundary, delivery date, acceptance contract, liability requirements, and budget. Suppliers return executable quotes. The buyer can reject all offers. An award creates a contract, delivery is verified, and payment settles under existing procurement rails.

This is a real market even if only three suppliers bid, contracts settle on net-30 terms, and a human contracting officer approves the award. Human involvement does not negate a market. It negates only a strong claim of fully autonomous machine commerce. The relevant liquidity measures are qualified response count, time to quote, completion rate, repeat participation, and ownership-adjusted concentration.

An approved-vendor network without repeated competition is not enough. It may be a procurement club or a collection of bilateral relationships. A buyer that always awards to the incumbent under a master contract has automated purchasing, not market formation.

### Stage 4 to stage 5: procurement becomes auction

A reverse auction can compress price discovery when requirements are sufficiently clear and several suppliers can satisfy them. Current U.S. federal acquisition rules state that reverse auctions may be appropriate only when market research indicates a competitive marketplace, multiple offerors can satisfy the requirement, and the specification encourages iterative bidding. The rules also bar a reverse-auction service provider and conflicted affiliates from bidding in the auction it hosts ([FAR Subpart 17.8, effective 13 March 2026](https://login.acquisition.gov/far/subpart-17.8)).

Those conditions expose the difference between an auction and dispatch. In dispatch, the controller observes or predicts costs and assigns a task. Suppliers do not choose bids, withhold capacity, or bear an award obligation. In an auction, suppliers strategically reveal information under a rule, can decline to bid, and bear consequences if they win.

Reverse auctions are fragile for AI services because quality is multidimensional and partially hidden. A lowest-price rule invites compute shading, under-scoped verification, strategic latency promises, or renegotiation after lock-in. Bidders that use the same foundation model, cloud, or pricing algorithm may appear independent while sharing common cost and failure shocks. Repeated auctions with transparent low bids can also make tacit coordination easier. In March 2024, the FTC and DOJ stated that competitors' joint reliance on shared pricing recommendations or algorithms can support unlawful coordination even when they retain some pricing discretion ([FTC and DOJ, 28 March 2024](https://www.ftc.gov/news-events/news/press-releases/2024/03/ftc-doj-file-statement-interest-hotel-room-algorithmic-price-fixing-case)).

An auction therefore passes only when the lot is comparable, technical eligibility is meaningful, bidder independence is adjusted for ownership and dependencies, the host is neutral, post-award quality is observable, and default has a remedy. The existence of an auction interface proves none of these conditions by itself.

### Stage 5 to stage 6: auctions become spot exchange

A spot market becomes possible when the object is fungible enough for repeated machine ordering. Examples include an authenticated API call, a bounded tool invocation, a fixed data entitlement, a token-throughput block, a latency-region class, or a standard verification service. Sellers publish executable prices or asks. Buyers submit bids or accept posted offers. Metering identifies delivery. Payment is authorized and settlement reaches defined finality.

Google's AP2 announcement of 16 September 2025 describes signed intent and cart mandates intended to establish authority, authenticity, and accountability across cards, transfers, and stablecoins. It is explicitly payment-agnostic and connects to existing payment methods ([Google AP2, 16 September 2025](https://cloud.google.com/blog/products/ai-machine-learning/announcing-agents-to-payments-ap2-protocol)). That makes AP2 an order-authority and evidence layer, not a final settlement rail. The distinction is material: a valid mandate can coexist with a failed bank transfer, chargeback, sanctions block, merchant default, or disputed delivery.

Spot exchange requires more than a protocol path. Inventory must be reservable, offers must be executable, metering must be attributable, and a legal person must stand behind each side. Liquidity must be demonstrated by fills, depth, spreads, slippage, and repeat cohorts after removing subsidies, retries, internal trades, and wash volume.

### Stage 6 to stage 7: spot calls become heterogeneous outcomes

Complex work does not become fungible merely because agents perform it. A security review, software migration, scientific analysis, or regulatory filing contains hidden context and state-dependent quality. The relevant institution is closer to a professional-services market than a token exchange.

The seller is a legal operator, firm, or human-agent team. It quotes price, deadline, method constraints, success probability, and warranty. Inventory is expert time, domain access, or project capacity. Verification occurs through milestones, tests, proofs, and independent expert judgment. Escrow and holdbacks reduce payment risk. Reputation must be conditioned on task difficulty and buyer behavior.

This can be a genuine market without autonomous legal personhood for the software agent. The agent is an instrument of a principal. The core principal-agent problem remains: the human or firm may not observe the agent's effort, while the buyer may not observe the operator's model, subcontractors, or hidden retries. Outcome payment can align incentives, but it can also intensify metric gaming and rejection of valuable hard cases.

### Stage 7 to stage 8: performance contracts become assurance and underwriting

Verification, audit, warranty, and insurance are separate economic services. A verifier sells information or evidence. An auditor sells an independent process opinion. A warranty provider promises a remedy. An insurer accepts a defined risk in return for premium, subject to limits, exclusions, reserves, capital, and claims adjudication.

These roles are not interchangeable. Perfect replay of a software trace can establish what happened without establishing negligence, legal causation, economic damages, or whether the event is covered. A success-probability estimate is not risk transfer. An SLA credit may be a service remedy rather than insurance. The legal classification depends on the obligation and jurisdiction.

The assurance market is especially vulnerable to capture. If the router selects the supplier, defines the metric, verifies the outcome, controls the reputation record, prices the guarantee, and adjudicates the claim, it can choose easy risks, suppress negative evidence, or redefine success after the fact. The apparent efficiency of integration removes independent checks. The market-formation test therefore treats verifier independence, loss-bearing solvency, claims rules, and appeal as first-order conditions.

### Stage 8 to stage 9: assurance becomes clearing

Clearing is the last stage because it manages obligations created elsewhere. A clearing layer can net positions, require collateral, coordinate delivery-versus-payment, define finality, and handle member default. It cannot create genuine demand, independent supply, comparable inventory, or competitive orders.

The BIS/CPMI-IOSCO Principles for Financial Market Infrastructures require clear settlement finality, controlled money-settlement risk, adequate liquid resources, collateral and margin where relevant, participant-default rules, and public procedures. These obligations survive automation ([PFMI, 16 April 2012](https://www.bis.org/cpmi/publ/d101.htm), [PFMI principle index](https://www.bis.org/pfmi/help/principleid.htm)).

A premature clearinghouse can create a liquidity illusion. It can process internal platform obligations, testnet transfers, or one anchor buyer's procurements and report gross volume. If the underlying orders are non-competitive, reversible, subsidized, or controlled by one principal, central clearing adds operational and credit concentration without creating a market.

## 3. Markets versus platforms and hierarchies

The platform boundary is determined by who contracts with whom and who bears residual risk.

In a hierarchy, the controller can direct supply, change internal prices, absorb losses, and bar entry. In a bundled platform, the customer contracts with the platform, while the platform privately buys inputs. In a marketplace, independent sellers make executable offers to buyers and retain delivery and liability obligations under a venue rulebook. An institution can operate all three forms in different layers.

Platforms have structural incentives to collapse markets back into hierarchy. They can bundle first-party agents at a zero apparent price financed by cloud or SaaS revenue, reserve better latency and data for their own services, pay hidden routing rebates, tie agent approval to proprietary identity and payment, retain reputation, acquire successful suppliers, and make nominally open protocols depend on proprietary extensions.

DOJ's 2023 Merger Guidelines explicitly distinguish competition between platforms, competition on a platform, and competition to displace one. They also identify the conflict that arises when the operator competes as a participant ([DOJ Guideline 9, 18 December 2023](https://www.justice.gov/atr/merger-guidelines/applying-merger-guidelines/guideline-9)). The EU Digital Markets Act supplies concrete institutional counterfactuals through anti-steering, direct contracting, restrictions on tying identification or payment services, switching rights, third-party installation, and the prohibition on favoring a gatekeeper's own products in ranking ([Regulation (EU) 2022/1925, 14 September 2022](https://eur-lex.europa.eu/eli/reg/2022/1925/2022-10-12/eng)).

Cloud infrastructure demonstrates why technical multi-homing is not enough. The UK CMA's final cloud investigation published on 31 July 2025 examined egress fees, interoperability, committed spend, licensing, switching, and multi-cloud, and identified significant market power concerns. A buyer may have many provider logos yet face high commercial switching costs ([CMA cloud market investigation](https://www.gov.uk/cma-cases/cloud-services-market-investigation)).

## 4. Routing versus run-all-and-select

Routing chooses a supplier or execution policy before observing every possible result. It is valuable when execution has non-trivial cost, latency, privacy exposure, rights constraints, or opportunity cost. The router estimates expected utility and commits resources selectively.

Run-all-and-select executes several suppliers on the same task and chooses after observing outputs. It can reduce ex-ante adverse selection because the buyer sees realized candidates. It also changes the game:

1. If every supplier is paid its posted execution price, the institution is a buyer-funded bake-off. There is no competitive bid and no supplier-side market allocation.
2. If only the winner is paid, it is a tournament. Suppliers bear speculative compute and may decline hard or expensive tasks.
3. If suppliers bid price and quality terms before execution and an enforceable rule awards the contract, it becomes a procurement mechanism.
4. If the evaluator is known, suppliers optimize toward it, creating benchmark leakage and Goodhart effects.
5. If outputs reveal proprietary methods or data, running all candidates expands rights and confidentiality risk.
6. If nominally different suppliers share a model or cloud, the extra runs add cost without adding meaningful diversity.

The run-all counterfactual is useful because it reveals what routing value actually consists of. If verification is perfect and free but execution remains costly, routing retains value as cost and capacity allocation. If execution is also free, instantaneous, private, and rights-neutral, run-all can dominate ex-ante model selection. The resulting problem is no longer which model call to buy. It is who owns the outputs, how attention is allocated, and how suppliers are rewarded.

## 5. Perfect and free verification

Perfect verification eliminates important frictions but not the market institution.

It removes or weakens output-quality adverse selection, many forms of hidden action, superficial certification, quality reputation, basic audit demand, and part of the risk premium. It makes pay-for-outcome and run-all mechanisms easier. It can commoditize suppliers whose only differentiation was unverifiable quality.

It does not establish authority, identity, legal liability, solvency, privacy, data rights, IP ownership, scarce compute, latency, availability, payment finality, tax, licensing, sanctions, switching, or remedies. It does not prevent collusion, self-preference, foreclosure, or a common cloud outage. It does not tell a court whether a technically verified output caused a legally compensable loss.

An assurance market for basic quality would contract under perfect verification. Insurance could remain for operational, legal, and systemic loss, but premiums would reflect residual risk rather than uncertainty about the immediate output. Reputation would retain value for availability, payment behavior, dispute conduct, and future capacity even if output quality were perfectly observable.

The falsifier is strong: if a claimed market disappears when verification becomes cheap, its scarce product may have been opacity or certification rent rather than the underlying service.

## 6. Supplier consolidation

Supplier count must be adjusted for ownership and dependency. Five agent brands running on one frontier model and one cloud are not five independent failure domains. Three bidders using the same router pricing service are not fully independent price setters.

Consolidation changes each mechanism:

- Internal control planes remain viable because they are not markets.
- Bundled platforms gain bargaining and foreclosure power.
- Directories retain many listings but lose substitutability.
- Procurement markets become oligopsony facing oligopoly.
- Reverse auctions become hollow or facilitate signaling among repeated bidders.
- Spot exchanges become distribution channels for a few wholesalers.
- Specialist niches may survive where domain assets are local.
- Insurers face greater correlated tail exposure and lower diversification.
- Clearing concentrates common operational and credit risk.

A market can exist under oligopoly, but the claims of liquidity, robust price discovery, and resilience become weaker. The decisive measures are parent ownership, common models, common clouds, common training data, common verifiers, and shared pricing or routing software.

## 7. Vertical trust conflict

Combining routing, verification, reputation, insurance, and adjudication creates a closed trust loop.

The router can favor suppliers that pay rebates. The verifier can define success to validate the router's choices. The reputation system can suppress failed or disputed tasks. The insurer can exclude tasks predicted to lose. The adjudicator can interpret ambiguous evidence in favor of the integrated platform. Each function then confirms the others.

The integrated operator's payoff can be written as:

`platform profit = usage fees + routing rebates + data rents + premiums - execution cost - paid claims - regulatory cost`

The buyer's payoff is:

`buyer utility = outcome value - price - monitoring cost - expected uncovered loss - switching cost`

These objectives diverge whenever the platform can increase fees or reduce paid claims without increasing buyer value. Integration can reduce transaction cost, but it also removes independent contradiction. The formation test therefore asks whether evidence is portable, metrics are fixed before execution, routing objectives and rebates are disclosed, reputation includes denominators and disputes, risk capital is segregated, and claims can reach a neutral forum.

## 8. Liquidity illusions

The following quantities are not liquidity by themselves:

- agent cards or catalog listings;
- API calls, especially retries;
- internal routing decisions;
- gross payment messages before reversals;
- downloads or GitHub stars;
- reserved capacity listed on several venues;
- transactions funded by platform credits;
- trade among entities under common control;
- one anchor buyer's procurement volume;
- imputed prices inside a bundle;
- testnet or sandbox activity;
- insurer quote volume without bound coverage.

Evidence of liquidity requires ownership-adjusted executable depth, actual fills, repeat buyers and sellers, spread and slippage, time to match, unsubsidized retention, low bypass leakage, and resilience when a major supplier or buyer exits. A thin market can still be real, but it must be labeled thin.

## 9. Opposite worlds

### World A: genuine machine market

An enterprise issues a signed and scoped purchasing mandate. Several ownership-independent suppliers multi-home across venues. A task has a machine-readable acceptance contract. Suppliers submit executable price-quality offers and bond performance. A neutral verifier checks delivery. Escrow or clearing links delivery and payment. Portable history follows each participant. An independent insurer prices residual risk. Defaults and appeals follow a public rulebook. Entry, congestion, capacity shocks, and demand changes measurably affect prices and allocation.

### World B: hierarchy with market vocabulary

An enterprise control plane chooses among API names under one or two master contracts. The suppliers share the same model and cloud. Prices are catalog rates or internal imputed costs. The platform controls routing, verification, reputation, and claims. Its remedy is a service credit while the enterprise bears most consequential loss. Billing settles monthly between enterprise and platform. A marketplace page contains listings but no executable offers. Agent traffic grows quickly without decentralized exchange.

### World C: machine-assisted procurement

Buyer agents automate RFQs and bid comparison among approved suppliers. Contracts and remedies are real, but humans approve material awards, tasks remain heterogeneous, liquidity is episodic, and settlement uses existing invoice and bank rails. This is a genuine procurement market but not autonomous machine clearing.

### World D: verification abundance without supplier markets

Outputs are perfectly and cheaply verified. Enterprises run several internal and bundled models, select the best result, and pay one platform subscription. Quality uncertainty falls, but independent suppliers do not price or contract directly. Verification improves hierarchy rather than creating a market.

### World E: consolidated machine commerce

Two cloud-platform-payment groups own most models, agent stores, identity approval, reputation, and settlement. Agents transact extensively inside each group. Cross-group interoperability is costly and reputation does not port. There are large commercial networks and perhaps competition between ecosystems, but limited competition on each platform and no neutral clearing market.

## 10. Hidden-confounder attacks

1. **Internal-GMV attack.** Internal chargebacks are counted as external transactions.
2. **Human-shadow attack.** A human selects every supposedly autonomous purchase.
3. **Master-contract attack.** Per-call routing occurs entirely inside one annual supplier contract.
4. **Common-parent attack.** Several brands share ownership.
5. **Common-stack attack.** Nominal competitors share model, cloud, data, verifier, or code.
6. **Demo-money attack.** Testnet, sandbox, credits, or unreconciled messages are called settlement.
7. **Subsidized-liquidity attack.** Incentives fund both sides and activity vanishes when credits end.
8. **Retry-demand attack.** Failures and retries are counted as new demand.
9. **Listing-supply attack.** Catalog entries are counted as active inventory.
10. **Imputed-price attack.** A bundled subscription is allocated to calls and presented as a market price.
11. **Capacity-double-count attack.** One capacity block is listed simultaneously on several venues.
12. **Verifier-ownership attack.** Seller, platform, and verifier share economics.
13. **Reputation-wash attack.** Sybils, reciprocal activity, or selective reporting inflate trust.
14. **Hidden-rebate attack.** A router appears neutral while suppliers pay for allocation.
15. **Benchmark-leakage attack.** Suppliers train on the evaluator and fail out of sample.
16. **Anchor-buyer attack.** One sponsor creates almost all demand.
17. **Reversibility attack.** Gross payment ignores refunds, chargebacks, and failed finality.
18. **Selection-denominator attack.** Only successful or easily verified tasks enter performance history.
19. **Jurisdiction attack.** Protocol interoperability hides tax, insurance, employment, sanctions, or licensing barriers.
20. **Goodhart attack.** The success metric becomes the target and reduces buyer value.
21. **Bypass-selection attack.** Strong buyers and sellers leave after discovery, leaving adverse risk on-platform.
22. **Dispute-suppression attack.** Contested trades are removed from public performance data.
23. **Supplier-financing attack.** Platform loans or guarantees make nominal sellers dependent on the venue.
24. **Latency-tier attack.** First-party agents receive hidden priority, making third-party quality appear lower.

## 11. Indicators and falsifiers

### Leading indicators of genuine formation

- Ownership-adjusted unique active buyers and sellers.
- Median number of independent qualified bids per task.
- Executable fill rate, depth, spread, slippage, and time to match.
- Repeat participation after subsidies expire.
- Share of purchases made under binding delegated mandates without human supplier selection.
- External settled value net of refunds, wash activity, internal transfers, retries, and credits.
- Multi-homing and successful switching rates.
- Direct bypass rates after first match.
- First-party versus third-party allocation after quality and risk adjustment.
- Portability and actual reuse of reputation across venues.
- Dependency concentration by model, cloud, data, verifier, and pricing algorithm.
- Default, dispute, refund, and claim-payment rates.
- Time to resolve disputes and percentage reaching neutral review.
- Verifier disagreement, calibration, and revenue independence.
- Underwriter limits, exclusions, capital, reserves, reinsurance, and paid claims.
- Price and allocation response to entry, congestion, supply outages, and demand shocks.

### Falsifiers

- No external legal counterparty or money settlement.
- All transactions are internal scheduler decisions.
- Catalogs have no executable orders.
- Almost all supply shares one parent or common dependency.
- Prices are administrative allocations inside bundles.
- Agents cannot bind principals and humans reconstruct each contract.
- Payment protocols generate messages but no final settled value.
- Underwriting consists only of small SLA credits with no material risk transfer.
- Verifier and underwriter are the same interested party with no independent appeal.
- Activity collapses when credits end.
- Reputation cannot leave the platform.
- There is no remedy beyond delisting.
- Technical switching exists but commercial switching does not.
- Gross activity grows without growth in competitive external purchases.
- A clearing layer launches before repeated underlying competitive trades exist.
- Perfect verification eliminates the purported market rather than improving its allocation.

## Conclusion

The rigorous dividing line is institutional, not technological. AI agents can automate hierarchy, procurement, marketplaces, and clearing alike. Autonomy does not choose among them.

The most plausible early external markets are thin procurement mechanisms: structured RFQs, reverse auctions for standardized lots, posted-price API exchange, specialist outcome contracts, and compute-capacity trades. Directories and protocols lower search and authorization costs but do not themselves create markets. Bundled platforms can generate large revenue while internalizing supplier choice. Clearing is meaningful only after underlying competitive obligations exist. Outcome underwriting is a separate risk-transfer institution whose formation depends on independent verification, real loss-bearing capital, correlated-risk control, claims governance, and legal enforceability.

The opposite world remains fully coherent: agent activity can expand by orders of magnitude while most economic decisions stay inside enterprises and vertically integrated platforms. Any claim of market formation is therefore falsifiable only through counterparty independence, executable allocation, external settlement, measured liquidity, portable reputation, default experience, and neutral dispute resolution.

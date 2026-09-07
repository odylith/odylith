# Round 2 Cross-Examination: Enterprise Economics and Institutional Authority

Date: 2026-08-05

Scope: This memo examines how enterprises, governments, and institutions may fund, centralize, delegate to, resist, insure, consolidate, or abandon autonomous systems as capability rises. It does not recommend a product, company, investment, or policy. It separates current facts from causal inferences and unresolved unknowns.

Labels used below:

- [Fact] means a claim supported by a linked primary or official source.
- [Inference] means a causal interpretation of facts, not an observed certainty.
- [Unknown] means an unresolved variable capable of reversing the scenario.

## Evidence baseline and measurement discipline

[Fact] Enterprise announcements are large but use different denominators. Microsoft reported more than 100 million monthly active Copilot users across commercial and consumer products and more than 230,000 organizations using Copilot Studio in its FY2025 annual report. Salesforce reported 5,000 Agentforce deals, including more than 3,000 paid deals, and $900 million of Data Cloud and AI annual recurring revenue on February 26, 2025. Accenture reported $5.9 billion of generative AI bookings in FY2025 while total bookings declined 1 percent. None of these measures, alone, proves that autonomous work reduced total cost, changed organization design, or produced net operating income. Sources: [Microsoft FY2025 annual report](https://www.microsoft.com/investor/reports/ar25/index.html), [Salesforce FY2025 results](https://investor.salesforce.com/files/doc_financials/2025/q4/CRM-Q4-FY25-Earnings-Press-Release-w-financials.pdf), and [Accenture FY2025 10-K](https://www.sec.gov/Archives/edgar/data/1467373/000146737325000217/acn-20250831.htm).

[Fact] Controlled and quasi-controlled labor evidence is narrower and more conditional. A field experiment across 66 firms and 7,137 knowledge workers found that active treated users spent about two fewer hours per week on email, but the researchers detected no material change in the quantity or composition of tasks from individual-level access. A customer support study found roughly 14 percent higher productivity, concentrated among less experienced workers, with negligible or slightly negative effects for the most experienced workers. The International Labour Organization's June 1, 2026 review found real but uneven and often unverified productivity effects; time savings generally had not yet translated into measured output, earnings, or employment. Sources: [NBER working paper 33795](https://www.nber.org/papers/w33795), [NBER customer support summary](https://www.nber.org/digest/20236/measuring-productivity-impact-generative-ai), and [ILO empirical review](https://www.ilo.org/publications/impact-genai-jobs-productivity-and-work-organization-review-empirical).

[Fact] Budget migration is nevertheless visible. Accenture disclosed $615 million of FY2025 business optimization costs, approximately 77,000 AI and data practitioners, and more than 550,000 people trained in generative AI fundamentals. Oracle disclosed a FY2026 restructuring plan with estimated costs up to $2.1 billion involving AI integration and recorded $1.8 billion during the year. These filings demonstrate reallocation and restructuring, not causal proof that AI generated the resulting benefits. Sources: [Accenture FY2025 10-K](https://www.sec.gov/Archives/edgar/data/1467373/000146737325000217/acn-20250831.htm) and [Oracle FY2026 10-K](https://www.sec.gov/Archives/edgar/data/1341439/000119312526277521/orcl-20260531.htm).

[Inference] The central measurement rule for this memo is therefore:

`seat or deal -> active use -> completed workflow -> accepted outcome -> captured economic value -> durable institutional legitimacy`

Each arrow can fail. A control system may improve execution without capturing a budget. A buyer may capture a budget without granting external authority. A technically valid outcome may still be legally unauthorized, contractually incomplete, or politically illegitimate.

## Debate 1: External authority versus customer-operated policy

### Strongest case for an external authority layer

[Inference] An external authority layer gains power when autonomous work crosses multiple model, cloud, application, and payment providers. No single application then sees the complete trajectory. A cross-provider authority can compare model performance, enforce a common policy, accumulate loss history, detect correlated failure, and offer a consistent audit surface. The value is not just lower inference price. It is the ability to say which identity acted, under which delegation, against which policy, with which evidence, and with what recovery behavior across provider boundaries.

[Fact] Existing public policy already recognizes the value of cross-functional and independent controls. US OMB Memorandum M-25-22, issued April 3, 2025, requires agencies to consider data and model portability, vendor lock-in, independent evaluation, ongoing monitoring, cost justification, and sunset criteria in AI acquisition. It also warns that vendors may use AI in contract performance without the government anticipating it. Source: [OMB M-25-22](https://www.whitehouse.gov/wp-content/uploads/2025/02/M-25-22-Driving-Efficient-Acquisition-of-Artificial-Intelligence-in-Government.pdf).

[Fact] Financial regulators likewise recognize that concentrated providers can become systemically important. The EU Digital Operational Resilience Act has applied since January 17, 2025. European supervisory authorities designated critical ICT third-party providers in November 2025 based partly on systemic importance and substitutability. Direct provider oversight complements, rather than replaces, each financial entity's responsibility. Sources: [EBA DORA oversight](https://www.eba.europa.eu/activities/direct-supervision-and-oversight/digital-operational-resilience-act/dora-oversight) and [critical-provider designation](https://www.eba.europa.eu/publications-and-media/press-releases/european-supervisory-authorities-designate-critical-ict-third-party-providers-under-digital).

[Inference] The strongest external-authority world therefore resembles a licensed utility. Enterprises delegate parts of identity, policy evaluation, evidence normalization, and incident coordination to a small number of supervised control points. Regulators accept the chokepoint because it is more examinable than thousands of local agents. Insurers accept it because loss telemetry is standardized. Enterprises accept it because switching among models and applications remains possible above the common authority plane.

### Opposite world: customer-operated policy remains sovereign

[Inference] The opposite world begins from a different premise: the party carrying legal responsibility needs operational control. Customer context includes confidential data, internal duties, worker agreements, jurisdictional rules, risk appetite, and emergency authority that an external provider cannot fully infer. In this world, an outside control point is another critical vendor, another subpoena surface, another concentration risk, and potentially an unacceptable observer of business intent.

[Fact] The EU AI Act places obligations on both providers and deployers of high-risk systems, including competent human oversight and log retention. It does not allow a deployer to transfer its obligations simply by buying a controlled service. Source: [EU AI Act](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=celex%3A32024R1689).

[Fact] Sovereignty procurement is already moving beyond data residency. In April 2026, the European Commission awarded a EUR 180 million sovereign-cloud procurement to four providers using 48 criteria spanning legal and jurisdictional control, data and AI, operations, supply chain, technology, security, and compliance. Source: [European Commission Sovereign Cloud Framework, June 1, 2026](https://commission.europa.eu/news-and-media/news/sovereign-cloud-framework-explained-2026-06-01_en).

[Inference] In the customer-sovereign world, policy runs inside the customer's cloud, network, or regulated enclave. External providers can supply models, assurance components, or updates, but the customer controls identity, keys, logs, policy, and final authorization. Evidence export is selective. A bank, defense organization, hospital, or government agency may tolerate an external model more readily than an external authority that observes every execution decision.

### Causal play-by-play

1. Local teams adopt multiple agents and models because capability differs by task.
2. Security and legal teams discover that no application has end-to-end visibility.
3. A central enterprise policy budget emerges under the CIO, CISO, or risk office.
4. Procurement tests two architectures: externally operated authority and customer-hosted policy.
5. If regulators, insurers, and customers accept standardized external evidence, the authority layer centralizes and may become a critical provider.
6. If jurisdiction, confidentiality, or accountability dominates, policy stays customer-operated while evidence formats standardize externally.
7. A hybrid equilibrium is possible: customer-side enforcement with third-party certification, loss aggregation, and dispute support.

### Hidden confounders

- A low external price may be subsidized by cloud or model consumption.
- A customer-hosted architecture may still depend on foreign code, silicon, or update channels.
- Provider-native integration can be mistaken for superior policy quality.
- An external authority may see only routed work; local scripts and shadow agents remain invisible.
- Regulatory acceptance in one sector or jurisdiction may not transfer to another.
- The legal defendant and the technical policy operator may be different entities.

### Discriminating indicators

- Share of enterprise contracts requiring customer-controlled keys and customer-side enforcement.
- Procurement requirements for evidence portability and provider-independent replay.
- Direct regulatory designation of AI control or identity providers as critical third parties.
- Percentage of governed workflows crossing more than one model or application provider.
- Frequency with which customers permit external retention of prompts, traces, or outcome evidence.
- Insurer pricing differences between provider-operated and customer-operated controls.

### Falsifier

[Inference] The independent external-authority thesis is falsified if enterprises consistently accept integrated provider controls, rarely use cross-provider execution, refuse external telemetry, and do not fund a separate authority budget. The pure customer-sovereignty thesis is falsified if regulators and insurers require standardized external supervision and customers cannot operate equivalent controls economically.

### Conditionally surviving opportunity categories

The categories that remain economically possible across both worlds are customer-hosted policy enforcement, portable evidence schemas, third-party certification, critical-provider supervision, key and identity custody, jurisdiction-aware execution, and exit or replay infrastructure. Which category captures value depends on where enforcement and legal accountability settle.

## Debate 2: Provider-native evidence versus independent proof

### Strongest case for provider-native evidence

[Inference] A model or application provider has privileged telemetry. It knows model version, hidden safety layers, tool calls, latency, retries, token use, content filters, identity bindings, and infrastructure events. Native evidence can be cheaper, more complete, and easier to correlate with incidents than an outside observer's reconstruction. Integrated suites also control user identity, data permissions, retention, and application state, reducing gaps between what an agent attempted and what the system committed.

[Fact] Microsoft documents tenant-level controls for agent authentication, knowledge sources, HTTP and MCP access, publishing channels, triggers, DLP, audit, retention, and shadow-AI discovery. AWS documents identity- and resource-based policies for Bedrock AgentCore. These are official product-control facts, not independent proof of control effectiveness. Sources: [Microsoft Copilot data policies](https://learn.microsoft.com/en-us/microsoft-copilot-studio/admin-data-loss-prevention), [Microsoft shadow-AI discovery](https://learn.microsoft.com/en-us/entra/global-secure-access/concept-shadow-ai-discovery), and [AWS AgentCore resource policies](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/resource-based-policies.html).

[Inference] In the strongest provider-native world, evidence is a feature of the execution substrate. Buyers prefer one signed, low-latency record from the party that operated the system. Independent proof adds cost, duplicates logs, and may lose access to proprietary state. Regulators examine the provider's control environment, similar to other critical outsourced infrastructure.

### Opposite world: independent proof becomes mandatory

[Inference] Provider evidence is self-attestation when the provider's revenue, liability, or reputation depends on the result. A provider can define success, omit inaccessible state, change a model, or bundle evidence with the service in ways that make switching expensive. Independent proof becomes more valuable as systems take consequential or irreversible actions.

[Fact] OMB M-25-22 directs agencies to use their own validation data where practicable, keep that data inaccessible to vendors, obtain access for independent evaluation, and require results detailed enough to reproduce. [OMB M-25-22](https://www.whitehouse.gov/wp-content/uploads/2025/02/M-25-22-Driving-Efficient-Acquisition-of-Artificial-Intelligence-in-Government.pdf).

[Fact] The SEC charged two investment advisers in March 2024 for false and misleading claims about their use of AI. The enforcement action demonstrates that AI assertions can themselves be regulated representations. Source: [SEC AI-washing enforcement](https://www.sec.gov/newsroom/press-releases/2024-36).

[Inference] In the independent-proof world, provider logs are necessary inputs but not the final evidence. A separate system verifies identities, policy versions, tool effects, business state, and outcome tests. The most important evidence is replayable and portable. A provider change does not destroy the institution's ability to explain or contest prior actions.

### Causal play-by-play

1. Providers expose increasingly rich native logs and controls.
2. Enterprises initially use them because integration cost is low.
3. A dispute, outage, model update, or regulator request reveals a missing or provider-defined fact.
4. Buyers add independent validation data, signed external timestamps, business-state checks, or separate evidence custody.
5. If independent evidence repeatedly agrees with native evidence, it may become a periodic audit rather than an inline control.
6. If disagreement is frequent or high consequence, independent proof moves into the transaction path.
7. Evidence architecture separates observability, verification, legal record, and business acceptance instead of calling all four "audit logs."

### Hidden confounders

- Native evidence may appear more accurate because it defines the event taxonomy.
- Independent proof may simply reproduce provider assumptions using the same model family.
- Replay can fail when models are nondeterministic or no longer available.
- Business outcomes may occur outside both evidence systems.
- More logs can create privacy, discovery, and trade-secret risk.
- A passing technical test may not prove legal authorization or economic value.

### Discriminating indicators

- Contractual rights to raw logs, model versions, prompts, tool inputs, and output replay.
- Frequency of independent validation data and provider-blind evaluations.
- Material disagreements between native and independent incident reports.
- Regulatory demands for evidence custody outside the provider.
- Switching events in which historical evidence remains usable.
- Insurance terms that accept or reject provider-generated records.

### Falsifier

[Inference] Independent proof loses its economic case if provider-native evidence is complete, portable, consistently accepted by courts, regulators, customers, and insurers, and cheaper than duplicated verification. Provider-only proof loses its case if consequential disputes repeatedly expose missing state, unverifiable claims, or conflicts of interest.

### Conditionally surviving opportunity categories

Portable evidence custody, provider-blind evaluation, signed execution receipts, business-state verification, model-version archives, dispute reconstruction, and periodic independent audit survive only where buyers attach value to evidence beyond provider observability.

## Debate 3: Delegation versus retained human and legal accountability

### Strongest case for broad machine delegation

[Inference] Delegation is economically attractive because continuous human confirmation eliminates much of autonomy's value. Agents can search, negotiate, schedule, buy, allocate resources, and execute contracts within standing authority. When identity, intent, scope, and revocation are machine-readable, legal systems can attribute outputs to an existing person or entity without granting the machine personhood.

[Fact] UNCITRAL adopted the Model Law on Automated Contracting on July 11, 2024. It supports legal recognition of automated contracting, output attribution, and rules for unexpected outcomes while preserving party autonomy and existing law. It does not establish AI personhood or a general AI governance code. Source: [UNCITRAL Model Law on Automated Contracting](https://uncitral.un.org/en/mlac).

[Fact] Visa's Trusted Agent Protocol signs agent identity, consumer recognition, intent, and payment information. Mastercard's Agent Pay program describes registered agents, tokenized credentials, and consumer-defined purchasing authority. Sources: [Visa Trusted Agent Protocol](https://developer.visa.com/capabilities/trusted-agent-protocol/trusted-agent-protocol-specifications/) and [Mastercard Agent Pay, April 29, 2025](https://www.mastercard.com/news/press/2025/april/mastercard-unveils-agent-pay-pioneering-agentic-payments-technology-to-power-commerce-in-the-age-of-ai).

[Inference] The strongest delegation world keeps the principal legally visible while making most acts automatic. Authority is scoped by value, time, counterparty, purpose, jurisdiction, and reversibility. Agents do not own property directly; the human, company, trust, or other legal wrapper does. The scarce asset becomes a reliable delegation record rather than a human click.

### Opposite world: accountability cannot be delegated

[Inference] Institutional legitimacy may require a natural person or accountable legal entity even when the machine is more accurate. Fiduciary duty, public coercion, employment, medicine, credit, and irreversible transfers involve duties that are not satisfied by authentication alone. A person can authorize an agent but may not be able to waive statutory rights or transfer the duty to understand and contest a decision.

[Fact] Delaware law requires every corporate director to be a natural person. The United Kingdom requires at least one natural-person director. Wyoming's DAO law allows algorithmic management through an LLC wrapper but requires a registered agent and upgradeable smart contracts. Sources: [Delaware Code Section 141](https://delcode.delaware.gov/title8/c001/sc04/), [UK Companies Act 2006 Section 155](https://www.legislation.gov.uk/ukpga/2006/46/pdfs/ukpga_20060046_en_001.pdf), and [Wyoming DAO statute](https://wyoleg.gov/NXT/gateway.dll/Statutes%2F2021%20Titles%2F879%2F1045%2F1046).

[Fact] US Regulation E limits consumer liability for unauthorized electronic transfers and prevents contracts from reducing statutory protection. An authenticated transaction can still be unauthorized under the governing definition. Source: [CFPB Regulation E](https://www.consumerfinance.gov/rules-policy/regulations/1005/6/).

[Fact] The EU AI Act requires high-risk deployers to assign human oversight to natural persons with competence, training, authority, and support. [EU AI Act](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=celex%3A32024R1689).

### Causal play-by-play

1. Low-risk delegation begins with scheduling, search, drafting, and small purchases.
2. Networks create agent-specific credentials and intent records.
3. Merchants and institutions distinguish agent identity from principal identity and authority.
4. Disputes expose differences among authentication, actual authority, apparent authority, consent, and benefit.
5. Legal rules allocate residual liability among principal, deployer, provider, merchant, and credential issuer.
6. High-frequency low-value actions become automatic; high-value, fiduciary, coercive, or irreversible actions retain named human or legal-person approval.
7. Synthetic organizations may manage assets through a wrapper, but property, tax, insolvency, and sanctions remain attached to recognized persons or entities.

### Hidden confounders

- A signed delegation may be broad because the user did not understand it.
- The agent provider may alter behavior after authorization.
- A merchant can verify identity without knowing whether the instruction remains current.
- Human approval can be a rubber stamp with no meaningful review.
- Firms may externalize agent error to consumers through terms that statutes later reject.
- Different jurisdictions can attribute the same automated act differently.

### Discriminating indicators

- Adoption of agent-specific delegated credentials rather than shared user tokens.
- Legal decisions distinguishing agent authentication from actual authority.
- Transaction limits, revocation speed, and dispute rates.
- Natural-person signature requirements for corporate, fiduciary, or public decisions.
- Statutes recognizing algorithmically managed entities while preserving human administrators.
- Allocation of chargebacks and losses among principal, merchant, bank, and provider.

### Falsifier

[Inference] Broad delegation is falsified if disputes, fraud, and consent failures remain high despite scoped credentials, causing institutions to restore contemporaneous human approval. Mandatory human accountability as an operational control is falsified if machine delegation becomes safer than human action and institutions retain humans only as symbolic defendants.

### Conditionally surviving opportunity categories

Delegated identity, purpose-bound credentials, revocation, transaction receipts, authority registries, legal-entity wrappers, dispute allocation, and accountable approval remain possible categories. Their value depends on whether law treats machine action as attributable delegation or as an unacceptable transfer of duty.

## Debate 4: Centralized governance versus local shadow-agent adaptation

### Strongest case for centralized governance

[Inference] Autonomous systems multiply nonhuman identities, permissions, tools, data paths, and irreversible actions. Central inventory and policy become necessary for separation of duties, incident response, retention, and regulatory examination. A local team cannot measure enterprise-wide concentration or prevent two agents from combining permissions that violate policy.

[Fact] Microsoft's security documentation describes discovering more than a thousand generative-AI applications, sanctioning or blocking apps, monitoring sensitive prompts, inventorying agent identities, restricting knowledge sources and HTTP or MCP tools, and retaining interactions. The June 2026 shadow-AI documentation explicitly identifies data leakage, compliance violations, and uncontrolled agent activity as risks. Sources: [Microsoft AI discovery](https://learn.microsoft.com/en-us/security/security-for-ai/discover) and [Microsoft shadow-AI discovery](https://learn.microsoft.com/en-us/entra/global-secure-access/concept-shadow-ai-discovery).

[Inference] In the strongest central-governance world, the CIO and CISO own a policy and identity plane. Business units can build agents only inside approved environments. Procurement consolidates providers. Irreversible actions require centrally defined thresholds. Central observability becomes a prerequisite for production access.

### Opposite world: local adaptation outruns central policy

[Inference] Shadow use often signals unmet needs, not merely worker indiscipline. Central platforms can be slower, less capable, or poorly matched to domain context. If policy approval takes months while free tools solve today's problem, local teams route around control. Complete centralization can also create a single failure domain and suppress the experimentation required to discover productive workflows.

[Fact] The UK National Cyber Security Centre's shadow-IT guidance treats shadow systems as risk but also as evidence of user needs that centralized technology has not met. Source: [NCSC shadow-IT guidance](https://www.ncsc.gov.uk/blog-post/spotlight-on-shadow-it).

[Inference] The strongest local world is not ungoverned. It is federated. Central teams define identity, evidence, prohibited actions, and escalation boundaries. Local teams choose models, context, and workflow logic inside those constraints. Control follows risk and action, not every prompt.

### Causal play-by-play

1. Individuals adopt unsanctioned tools because they are immediately useful.
2. Sensitive data and credentials begin to flow through untracked systems.
3. Security deploys discovery, blocking, and DLP.
4. Users lose capability or route through unmanaged devices and accounts.
5. Central IT creates sanctioned sandboxes, faster approvals, and local builder roles.
6. If local completion and compliance both improve, a federated model stabilizes.
7. If incidents continue, control recentralizes; if central products lag badly, shadow adaptation persists.

### Hidden confounders

- Detection growth can mean better visibility rather than more shadow use.
- Blocking metrics can hide migration to personal devices or copied data.
- Central platform success may reflect bundled licensing rather than user preference.
- Local teams may omit cleanup labor and downstream risk from their productivity claims.
- Central teams may classify every local variation as risk to protect organizational power.
- Business units may retain separate budgets that central telemetry cannot see.

### Discriminating indicators

- Ratio of shadow agents discovered to sanctioned agents actively completing work.
- Time from local request to approved production access.
- Use of personal accounts, unmanaged devices, and copied data after blocking.
- Percentage of policy violations remediated through education or sandboxing rather than prohibition.
- Local override and exception rates.
- Incident severity under centralized versus federated governance.

### Falsifier

[Inference] Pure centralization is falsified if shadow use remains high, sanctioned completion remains low, and local environments outperform without increasing losses. Pure localism is falsified if permission combinations, data leakage, or correlated incidents cannot be controlled without enterprise-wide identity and policy.

### Conditionally surviving opportunity categories

Agent inventory, shadow discovery, sanctioned sandboxes, local policy templates, federated identity, risk-tiered approvals, business-unit chargeback, and enterprise-wide incident correlation remain conditional categories. Their boundaries depend on whether control can be centralized without making useful local action too slow.

## Debate 5: Trusted superintelligence and the collapse of conventional oversight

### Strongest case that conventional oversight collapses

[Inference] In a trusted-superintelligence world, human review becomes less accurate, slower, and more expensive than the system being reviewed. A requirement that a human understand each action becomes impossible for long trajectories operating at machine speed. Separation of duties may shift from human-versus-machine to machine-versus-machine: one system proposes, another verifies, a third monitors rights and resource limits, and a fourth reconstructs disputes.

[Inference] Traditional scarcities can then weaken. Expertise, planning, contract drafting, compliance checking, and operational coordination become abundant. But authority does not disappear; it moves. The provider or institution controlling identity, memory, compute, policy, and settlement can become a quasi-sovereign. A world described as post-scarcity may still contain permission scarcity, exit scarcity, jurisdiction scarcity, and provider-controlled reputation.

[Inference] The strongest case for collapsed conventional oversight assumes: very high calibrated reliability; adversarial robustness; interpretable commitments even if reasoning is not human-readable; stable goals; effective machine checks; and compensation for the remaining tail. Human roles move to constitutional design, selection of protected values, allocation of residual liability, and appeal, rather than transaction-by-transaction review.

### Opposite world: procedural legitimacy survives technical supremacy

[Inference] Accuracy is not the only source of legitimacy. Citizens may demand human accountability for punishment, war, benefits, employment, medicine, or fiduciary decisions because these acts express public or moral authority. A superhuman system can calculate an answer yet lack consent to rule. The human role can persist as a constitutional defendant, representative, or source of democratic authorization even when operational review adds little technical value.

[Fact] Current law reflects this distinction. Delaware requires natural-person directors; the EU AI Act assigns high-risk oversight to competent natural persons; Regulation E preserves consumer rights despite electronic authentication; and UNCITRAL recognizes automated contracts without creating machine personhood. These are present baselines, not proof that future law cannot change. Sources: [Delaware Code Section 141](https://delcode.delaware.gov/title8/c001/sc04/), [EU AI Act](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=celex%3A32024R1689), [CFPB Regulation E](https://www.consumerfinance.gov/rules-policy/regulations/1005/6/), and [UNCITRAL MLAC](https://uncitral.un.org/en/mlac).

### Causal play-by-play

1. Machine recommendations outperform average humans in bounded domains.
2. Human review initially remains mandatory but becomes a throughput bottleneck.
3. Institutions compare human override outcomes with machine outcomes.
4. If overrides worsen results, review shifts to exception classes and constitutional constraints.
5. Automated verifiers and monitors gain delegated authority over routine execution.
6. A provider or sovereign institution controlling the verification ensemble gains political power.
7. Legitimacy either reconstitutes around public charters, appeals, portability, and liability, or collapses into provider permission and private arbitration.

### Hidden confounders

- Apparent superhuman performance may reflect benchmark selection or inaccessible human cleanup.
- Verifiers can share training data, assumptions, and correlated failure with actors.
- Trust can be manufactured by provider control of metrics and communication.
- High average reliability does not bound catastrophic tail behavior.
- Humans may override rarely but remain essential for novel values or constitutional change.
- A provider-controlled identity and memory layer can make exit practically impossible even if alternatives exist.

### Discriminating indicators

- Comparative harm from human overrides versus machine decisions.
- Share of consequential decisions reviewed only by other machines.
- Public acceptance of machine-made decisions after adverse outcomes.
- Legal movement from human oversight to human appeal or charter authority.
- Portability of identity, memory, reputation, property records, and delegated authority.
- Concentration of compute, credential issuance, settlement, and arbitration in the same provider.
- Tail-loss and correlated-failure evidence across verifier ensembles.

### Falsifier

[Inference] Conventional oversight collapse is falsified if human review continues to add material safety or legitimacy even after machines dominate routine accuracy. Persistent-human-legitimacy is falsified if societies accept machine decisions, appeals remain effective, and named humans add neither technical nor democratic value.

### Conditionally surviving opportunity categories

Constitutional policy specification, machine-on-machine verification, rights monitors, public-interest audit, appeal and redress, identity and memory portability, sovereign control, and correlated-risk measurement remain conditional categories. In a highly trusted world, value migrates away from routine review toward constitutional and systemic control.

## Debate 6: Budget migration from seats and pilots to consumption, operations, and assurance

### Strongest case for budget migration

[Inference] Seat pricing fits human-facing assistance. Autonomous execution behaves more like infrastructure or outsourced operations: cost varies by work volume, model use, retries, tools, verification, and exceptions. Once a workflow has a measurable accepted outcome, the economic buyer shifts from an innovation leader or CIO to the function P&L owner and CFO. Spending can then replace labor, BPO, overtime, error reserves, or lost demand.

[Fact] OMB M-25-22 promotes performance-based acquisition, quality-assurance surveillance, performance incentives, ongoing evaluation, and sunset criteria. This is an official example of procurement moving from capability claims toward measured outcomes. [OMB M-25-22](https://www.whitehouse.gov/wp-content/uploads/2025/02/M-25-22-Driving-Efficient-Acquisition-of-Artificial-Intelligence-in-Government.pdf).

[Fact] Insurance can also become a budget owner or gatekeeper. The NAIC model bulletin expects risk-proportionate AI governance across the insurance lifecycle, including third-party systems. Munich Re markets AI performance coverage conditioned on technical due diligence. Sources: [NAIC model bulletin](https://content.naic.org/article/naic-members-approve-model-bulletin-use-ai-insurers) and [Munich Re aiSure](https://www.munichre.com/en/solutions/for-industry-clients/insure-ai/ai-whitepaper.html).

[Inference] The mature migration path is:

`personal tool -> departmental pilot -> enterprise platform -> workflow operations -> assurance and evidence -> premium, bonding, or capital`

At each stage, a different coalition controls the budget. Developers and innovation teams fund experiments. CIO and CISO fund shared control. COO and function leaders fund production. CFO and risk committees fund assurance, insurance, and capital.

### Opposite world: seats and pilots remain dominant

[Inference] The opposite world appears when work remains individual, output demand is inelastic, coordination does not change, and time saved cannot be captured. The enterprise keeps buying seats because assistance improves employee experience or quality, but does not remove a cost base. Pilots persist because managers cannot define accepted outcomes or compare cleanup and exception costs with a human baseline.

[Fact] The NBER cross-firm experiment and the ILO 2026 review support this caution: individual time savings did not automatically change task composition, output, earnings, or employment. Sources: [NBER working paper 33795](https://www.nber.org/papers/w33795) and [ILO empirical review](https://www.ilo.org/publications/impact-genai-jobs-productivity-and-work-organization-review-empirical).

### Causal play-by-play

1. Employees and developers obtain free or seat-priced access.
2. Departments fund pilots and consultants around visible use cases.
3. Security and IT add identity, data, integration, and observability costs.
4. A function leader measures accepted outcome, exception, latency, and total review cost.
5. If value is captured, labor or service budgets migrate to consumption and operations.
6. If loss is measurable and diversifiable, assurance, premium, or reserve budgets emerge.
7. If value stays as unallocated time savings, the enterprise returns to seat pricing or cancels the pilot.

### Hidden confounders

- Bundled seats can make consumption appear free while cloud cost rises elsewhere.
- Consultant bookings can reflect experimentation rather than durable operations.
- Headcount changes can come from macroeconomics or ordinary restructuring.
- Cleanup and exception labor may remain off-book.
- Demand expansion can absorb productivity without reducing labor.
- A function can capture benefits while transferring risk to customers, workers, or another department.
- Insurance premiums can look like proof of safety while excluding the material loss class.

### Discriminating indicators

- Ratio of paid seats to active users and completed workflows.
- Cost per accepted outcome including review, retries, integration, and incidents.
- Movement of budget from innovation or CIO accounts to function P&L accounts.
- Reductions in BPO, overtime, error reserves, or unfilled requisitions linked to measured workflows.
- Share of AI spend devoted to identity, data, evaluation, operations, and assurance rather than models.
- Premium, bonding, reserve, or indemnity terms tied to execution evidence.
- Renewal based on business outcome rather than licensed capacity.

### Falsifier

[Inference] The operations-and-assurance migration is falsified if spending remains seat-based, function owners do not assume the budget, accepted-outcome economics do not improve, and no substitutive cost moves. The persistent-seat world is falsified if workflow volumes, autonomous completion, and risk transfer produce stable unit economics and measurable P&L capture.

### Conditionally surviving opportunity categories

Usage accounting, accepted-outcome measurement, integration, exception operations, evaluation, AI FinOps, evidence retention, indemnity, insurance, and exit tooling survive only where a buyer can connect them to a controlled cost or loss pool.

## Debate 7: Moratorium, abandonment, and selective re-entry

### Strongest case for moratorium or abandonment

[Inference] Autonomous systems can be abandoned for two different reasons: harm or value failure. Harm includes privacy breach, discrimination, unauthorized payment, invalid contract, security compromise, regulatory action, or correlated operational loss. Value failure includes low use, excessive review, unstable models, vendor price changes, and no captured output. Either can displace the innovation coalition with a board, legal, security, worker, customer, regulator, or insurer coalition.

[Fact] The EU Product Liability Directive treats software, including AI, as a product and preserves no-fault liability for defective products placed on the market or put into service after December 9, 2026. Manufacturers can remain responsible for defects arising from software or related services under their control. Source: [EU Product Liability Directive](https://eur-lex.europa.eu/eli/dir/2024/2853/oj).

[Fact] AI regulation also changes during adoption. Colorado's 2024 AI law was delayed and then replaced by a 2026 automated-decision law taking effect January 1, 2027. The policy churn itself raises planning cost even before enforcement. Source: [Colorado Attorney General rulemaking page](https://coag.gov/ai/).

[Fact] New York City already prohibits use of covered automated employment decision tools without a recent bias audit, public information, and notice. Source: [NYC Automated Employment Decision Tools](https://www.nyc.gov/site/dca/about/automated-employment-decision-tools.page).

[Inference] In the strongest abandonment world, an incident exposes that logs are incomplete, human oversight was nominal, or the vendor contract transfers too little risk. The board suspends action-taking agents. Budget returns to manual continuity, remediation, legal defense, and controls. Insurers exclude the use case. Regulators or workers make re-entry expensive. The system may continue as an advisory tool while autonomy disappears.

### Opposite world: incidents cause narrower re-entry, not abandonment

[Inference] Complete moratoria are unstable when employees retain access to cheap tools, competitors capture real gains, and manual continuity is costly. Institutions often respond by shrinking the action space, adding evidence and approval, changing providers, or moving the system inside a sovereign boundary. Failure can therefore increase demand for control while reducing demand for autonomy.

### Causal play-by-play

1. A production system scales faster than evidence, ownership, or exception capacity.
2. A severe incident or persistent value gap reaches the board or regulator.
3. The innovation sponsor loses authority to legal, security, risk, workers, or insurers.
4. Irreversible actions are disabled; manual continuity and forensic reconstruction begin.
5. Contracts, data rights, logs, and loss allocation determine whether the vendor relationship survives.
6. If the workflow remains valuable, re-entry occurs with narrower scope, dual approval, customer-operated policy, stronger proof, or insurance.
7. If accepted-outcome economics remain negative or legitimacy does not recover, the workflow is permanently retired.

### Hidden confounders

- An incident may be blamed on AI when the root cause is poor identity, data, or ordinary process design.
- A moratorium can be symbolic while shadow use continues.
- Falling use may reflect economic conditions rather than loss of trust.
- Vendor indemnity can mask rather than reduce operational risk.
- A temporary model regression can be mistaken for a structural failure.
- Competitor claims may exaggerate the cost of staying manual.
- Regulatory delay can be mistaken for regulatory acceptance.

### Discriminating indicators

- Board-level risk escalation, emergency disablement, and material-control disclosures.
- Reduction in action permissions rather than only model changes.
- Growth in manual exception staff and continuity spending.
- Insurance exclusions, premium increases, or coverage withdrawal.
- Contract renegotiation for indemnity, logs, portability, and model-change notice.
- Re-entry limited by value, action type, jurisdiction, or reversible transaction class.
- Permanent retirement after the sunset review.

### Falsifier

[Inference] The moratorium thesis is falsified if material incidents do not change budgets, permissions, insurance, or adoption. The selective re-entry thesis is falsified if shadow demand disappears, competitors do not capture an advantage, and institutions permanently restore human execution at acceptable cost.

### Conditionally surviving opportunity categories

Incident forensics, rollback, kill switches, manual continuity, evidence reconstruction, contract exit, model-change control, narrow-scope reauthorization, insurance review, and sunset evaluation survive only where institutions retain a path between unrestricted autonomy and permanent abandonment.

## Cross-world matrix

The axes below are independent. "Trusted" means institutionally legitimate, not merely benchmark-accurate. "Expensive" means total risk-adjusted cost, including integration, review, liability, and sovereignty.

| Control/provider structure | Cost | Trust | Enterprise equilibrium | Authority equilibrium |
|---|---:|---:|---|---|
| Concentrated | Cheap | Trusted | Suite or control utility captures operations budget | Licensed provider with public obligations |
| Concentrated | Cheap | Untrusted | Cheap capability plus high monitoring and remediation | Contested provider sovereignty |
| Concentrated | Expensive | Trusted | Sovereign or regulated critical stack | National bloc with audited accountability |
| Concentrated | Expensive | Untrusted | Moratorium, manual fallback, or breakup | State seizure or human-only consequential action |
| Plural | Cheap | Trusted | Federated local agents and open competition | Human-principal delegation on common rails |
| Plural | Cheap | Untrusted | Shadow-agent bazaar and high dispute cost | Consent and finality rollback |
| Plural | Expensive | Trusted | Narrow specialist workflows with proof and insurance | Insurability-gated delegation |
| Plural | Expensive | Untrusted | Advisory pilots with little captured value | Human signatures remain operationally mandatory |

## Buyer and authority migration map

| Stage | Dominant sponsor | Budget source | Authority conflict | Observable failure |
|---|---|---|---|---|
| Personal use | Worker or developer | Free tier or expense | Policy evasion versus unmet need | Shadow data and credentials |
| Pilot | Business unit or innovation team | Departmental experiment | Speed versus evidence | Demo success with no baseline |
| Platform | CIO, CTO, CISO | Shared IT and security | Standardization versus local fit | Shelfware or central bottleneck |
| Operations | COO and function owner | Labor, BPO, service delivery | Autonomy versus exception ownership | Hidden review and cleanup cost |
| Assurance | CFO, risk, general counsel | Reserve, audit, premium | Evidence versus confidentiality | Coverage gaps and disputed loss |
| Sovereignty | Board, regulator, state | Critical infrastructure budget | External scale versus jurisdiction | Cost premium or provider dependence |
| Moratorium | Board, regulator, insurer, workers | Remediation and continuity | Competitive pressure versus legitimacy | Shadow re-entry or permanent retirement |

## Partial-observability traps across all debates

- Purchased licenses, active users, deployed agents, completed actions, accepted outcomes, and captured P&L are different denominators.
- A control plane observes only work routed through it.
- "Verified" can mean a technical test passed while legal authorization, customer acceptance, or business value remains unresolved.
- Human review can be nominal if the reviewer lacks time, information, competence, or override power.
- Authentication proves possession of a credential, not informed consent or fiduciary compliance.
- Average reliability hides correlated and fat-tail failure.
- Insurance availability does not prove that material loss classes are covered or that claims capacity is adequate.
- Regulatory non-enforcement, pilot permission, or delayed rules do not establish durable legitimacy.
- Cross-customer learning can be technically effective and contractually prohibited at the same time.
- Workforce reductions can coincide with AI investment without being caused by AI productivity.

## Non-prescriptive boundary statement

No single authority or enterprise architecture survives every world. External authority has the strongest causal case when execution is cross-provider, evidence is portable, regulators accept a supervised chokepoint, and customers permit telemetry. Customer-operated policy has the strongest case when jurisdiction, confidentiality, fiduciary responsibility, or sovereignty dominates. Provider-native evidence dominates when integrated telemetry is complete and institutionally accepted; independent proof dominates when conflicts, portability, or disputed outcomes matter. Delegation expands when scope and attribution are reliable; retained human or legal accountability persists where authority is constitutional, fiduciary, coercive, or non-waivable. Central governance expands after concentration or incidents; local adaptation persists when central systems cannot meet user needs. Trusted superintelligence reduces routine review but does not automatically resolve political legitimacy, property, consent, or exit. Operations and assurance budgets emerge only after accepted outcomes connect to a substitutive cost or insurable loss. Moratoria become durable only when manual continuity is affordable and neither shadow demand nor competitive pressure forces selective re-entry.

These are conditional equilibria and falsifiable causal paths, not a prescriptive conclusion.

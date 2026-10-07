# Coaxing Protocol

Version 0.2, last revised 9 September 2026.

The plain-English question set that pulls data design requirements out of people who have never heard the word "grain". Each question is paired with the technical attribute its answer reveals. Questions are asked in layer order. Layer 00 gates everything: a request that cannot clear it after two attempts is flagged for review, and the gap carries forward into the output.

Questions marked **rarely asked** are the ones most often skipped and most expensive to retrofit.

## Standing rules

**Problem before features.** Requesters hand you their guess at a solution. Open on what's broken, never on what they want built.

**Never ask the real question.** Ask the one whose answer reveals it. Nobody outside the data team can answer "what's your grain"; everyone can answer "what would one row be".

**Every answer must land.** If a question doesn't populate a field in the output spec, cut it. The interview is a form-filler, not a conversation.

## 00. The problem

Always first, never skipped. Everything downstream is invalid if the stated problem is actually a proposed solution in disguise.

> What's happening today that shouldn't be?

Reveals: The actual problem, separated from the requester's proposed solution

> Walk me through what you do today when you need this.

Reveals: Current process · hidden source systems · the shadow spreadsheet nobody mentions

> How often does this bite you?

Reveals: Frequency · evidence for prioritisation

> Who else deals with this same problem?

Reveals: Blast radius

> If this were fixed, what would you do differently on Monday? **[rarely asked]**

Reveals: The activation use case: what the data is actually *for*

**Why it matters**: This is the single most important input to semantic layer design. A request with no answer here is a report nobody will open.

> How would you know it worked?

Reveals: Acceptance criteria, in the requester's own words

## 01. The decision

What kind of thinking the data supports. Determines whether you're building a monitor, an investigation surface, or a one-off answer.

> What are you actually asking: how much, how many, which ones, or has something changed?

Reveals: Measure · count · filtered detail list · time series

> Do you check this on a schedule, or go looking when something feels wrong?

Reveals: Monitoring vs. investigative. Decides whether drill paths and self-serve exploration are in scope

> Who else will look at this, and are they asking the same question?

Reveals: Audience breadth: whether the model must generalise beyond one report

## 02. Shape of the answer

The skeleton of the semantic layer: what gets measured, and what it gets sliced by.

> If I put this on one slide, what's the number in the middle?

Reveals: Primary measure(s) and their aggregation

> What would you want to break that number down by?

Reveals: Dimensions. Direct semantic layer input

> Would you ever click a total to see what's inside it?

Reveals: Drill-through requirement. Forces the grain conversation early

> Is there anything you'd compare it against: last year, a target, another team?

Reveals: Time intelligence · benchmark joins · target data sourcing

## 03. Grain

The hardest thing to ask directly and the most expensive thing to get wrong. Ask it as a spreadsheet, never as a schema.

> If I handed you a spreadsheet of this, what would one row be: one customer, one order, one day? **[rarely asked]**

Reveals: Grain, answerable by anyone

**Why it matters**: The whole model hangs off this. Asked in schema language it gets a blank stare; asked as a spreadsheet it gets a correct answer almost every time.

> Could that ever show up more than once in the spreadsheet?

Reveals: Fan-out and double-count risk

> Could one of these ever belong to more than one group at the same time?

Reveals: Many-to-many cardinality. The thing that silently breaks totals

## 04. Source and truth

Where the data comes from, and which version wins when they disagree.

> Where do you look today when you need this?

Reveals: Source systems, and usually a spreadsheet nobody had declared

> If two systems showed different numbers, which would you believe? **[rarely asked]**

Reveals: System of record · reconciliation rules · tolerance

**Rarely asked**: Skipping it means the reconciliation logic gets decided by whoever writes the join, and defended by nobody when the numbers are challenged.

> Who types this in, and when in the process?

Reveals: Entry latency · completeness windows · quality risk at source

> Does anyone go back and correct it after the fact? **[rarely asked]**

Reveals: Restatement and late-arriving data handling

**Rarely asked**: Determines whether incremental loads are safe or whether you need snapshots. Discovering this after go-live means a rebuild.

## 05. Dependency and stewardship

Nobody can tell you who owns the data. Everybody can tell you who uses it, who complains when it breaks, and who settles arguments about it. Ownership is inferred from those answers, never asked for directly.

> Which teams would notice if this stopped updating?

Reveals: Downstream dependencies · blast radius · candidate domain membership

> Who do you go to when the numbers look wrong? **[rarely asked]**

Reveals: The de facto steward: the person already doing the job, named or not

**Why it matters**: Organisations without formal ownership still route around it informally. This question finds the person the org already trusts, which is better evidence than an org chart.

> If two people disagreed about what this should say, who'd settle it? **[rarely asked]**

Reveals: Decision rights: the working definition of ownership

**Why it matters**: Ownership is who arbitrates, not who's listed. This is the answer that makes a definition defensible when it's challenged later.

> Once you've got this, where does it go next?

Reveals: Onward flows · exports leaving the platform · shadow reporting built downstream

> Which process stalls if this is late or wrong?

Reveals: Criticality tier. Justifies the freshness SLA and monitoring spend

> Who'd need to sign off on someone new seeing this?

Reveals: De facto access approver → role design input

## 06. Time

Freshness, history, and whether the past is allowed to change.

> How fresh does this need to be: good enough this morning, or right this second?

Reveals: Freshness SLA · batch vs. streaming · the cost conversation

> Is there a moment when this matters most: month end, Monday morning?

Reveals: Schedule alignment and peak-load timing

> How far back do you need to see?

Reveals: History depth · retention policy

> Do you need to see what it looked like back then, or only how it looks now? **[rarely asked]**

Reveals: Slowly changing dimensions: history tracking vs. current state

**Rarely asked**: Almost never volunteered, and retrofitting it means reloading history you no longer have. Ask it every time.

## 07. Definitions

This layer *is* the semantic layer. Everything here becomes a metric definition, a filter, or a synonym.

> When you say "active", what makes something count?

(Asked once per ambiguous term the interview has picked up; "active" is an example.)

Reveals: The business rule behind the term → metric definition

> Would the finance team define that the same way? **[rarely asked]**

Reveals: Competing definitions: whether you need one blessed metric or several named variants

**Why it matters**: Two teams with two definitions and one metric name is how a semantic layer loses trust in its first month.

> Is there anything that shouldn't count: tests, internal accounts, cancellations?

Reveals: Exclusion filters. The usual root cause of "the number's wrong"

> What do you call this? Does anyone call it something else? **[rarely asked]**

Reveals: Synonyms and aliases for the semantic model

**Why it matters**: Feeds natural-language querying directly. A model that only knows the warehouse's name for a thing can't answer a question phrased in the business's name for it.

## 08. Access and sensitivity

Asked during design, not after the access request queue forms.

> Should everyone looking at this see all of it, or only their own part?

Reveals: Row-level security requirement

> Is any of this personal or sensitive: names, pay, anything you'd not want widely shared?

Reveals: Classification · masking · handling obligations

> Who's likely to ask for this next?

Reveals: Role design. Builds for the second requester before they arrive

## 09. Scale

Two questions, asked in orders of magnitude. Nobody knows their row counts; everybody knows whether it's hundreds or millions.

> Roughly how much data is this: hundreds, thousands, or millions of records?

Reveals: Volume sizing · warehouse sizing · clustering worth considering

> Is that number growing fast?

Reveals: Growth headroom and partition strategy

## Where each layer lands

The output spec is fixed. Every layer populates a known section, which is what makes the interview mechanical rather than freeform.

- **00** Problem statement, affected users, and success criteria
- **01·02** Measures, dimensions, and the activation pattern
- **03** Grain declaration and cardinality warnings
- **04** Source-to-target mapping, system of record, reconciliation rules
- **05** Dependency map, inferred stewardship, criticality tier
- **06** Freshness SLA, history depth, change-tracking strategy
- **07** Semantic layer: metric definitions, filters, synonyms
- **08** Access model and data classification
- **09** Sizing and growth assumptions

## The layer that compounds

Every other layer produces a spec for one request and is then finished. Layer 05 is different:
each interview adds edges to a dependency and stewardship map the organisation almost certainly
does not have written down anywhere.

Run twenty interviews and you have twenty specs, and also a usage graph showing which teams depend
on what, who arbitrates each definition, and which datasets have no identifiable steward at all.
The gaps are the most useful output of the lot.

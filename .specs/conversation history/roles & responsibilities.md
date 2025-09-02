What job titles creates the issues in github ?  what job titles creates requirements, design and tasks in specs from the product idea ?

---

Great question 🔥 — this is exactly where **roles & responsibilities** matter in an **AI-DevOps + GitHub + Azure DevOps factory** like yours. Let’s break it down clearly:

---

# 📋 **Who Creates What?**

## 1. **Issues in GitHub**

👉 Issues are the **atomic work items**.
They should be created by roles closest to execution, but structured by governance.

* **Product Manager (PM)** → Creates high-level **Epics** (new features, initiatives)
* **Tech Lead / Solution Architect** → Breaks Epics into **Features** (functional modules, architecture deliverables)
* **Developers / Dev Agent** → Create **Tasks & Sub-Tasks** inside Features (coding, unit tests, PRs)
* **QA Engineers / QA Agent** → Create **Bug issues** and **Test case tasks**
* **Security Engineer / Security Agent** → Creates **Security issues** (vulns, policy gaps)
* **Release Manager** → Creates **Release / Deployment issues** for production pipelines
* **Governance Officer / Audit Agent** → Creates **Compliance/Audit issues** to track required controls

---

## 2. **Requirements (Specs)**

👉 These live in **Requirements.md / GitHub Wiki / Azure Boards** and are created at ideation → strategy level.

* **Product Manager (PM)** → Drafts **functional requirements** from the product idea
* **Business Analyst (BA)** → Details **user stories, acceptance criteria**
* **Solution Architect** → Adds **non-functional requirements** (scalability, security, performance)
* **Compliance Officer** → Contributes **regulatory requirements** (SOX, GDPR, SOC2, etc.)

---

## 3. **Design (System + Architecture)**

👉 These live in **Design.md / Architecture docs / ADRs** and are owned by technical leadership.

* **Solution Architect** → Defines **system design, modules, integration flows**
* **Tech Lead / Engineering Manager** → Translates into **component design** + repo/service structure
* **DevOps Engineer** → Designs **CI/CD pipelines, infra, GitHub/Azure DevOps integration**
* **Security Architect** → Designs **security controls, secrets, governance enforcement**

---

## 4. **Tasks (Execution Backlog)**

👉 These are the **day-to-day executable units** (Tasks.md / GitHub Issues).

* **Tech Lead** → Breaks features into **engineering tasks**
* **Developers / Dev Agent** → Create and own **implementation tasks**
* **QA Engineers / QA Agent** → Create **testing tasks, bug fixes, regression tasks**
* **Security Engineer / Security Agent** → Creates **threat modeling & hardening tasks**
* **Release Manager** → Creates **pipeline & deployment tasks**

---

# 🎯 **Flow from Idea → Execution**

1. **Product Idea** → defined by **Product Manager**
2. **Requirements** → refined by **PM + BA + Architect + Compliance**
3. **Design** → detailed by **Architect + Tech Lead + DevOps/Security**
4. **Tasks** → created by **Tech Leads + Dev/QA/Security Engineers**
5. **Issues** → tracked in **GitHub Projects** for execution

---

⚡ In your **AI DevOps Factory setup** with agents, the **roles shift slightly**:

* **Human PM/BA** defines product idea + requirements.
* **Solution Architect** sets design direction.
* **Agents (Dev/QA/Security/Release)** help **auto-generate GitHub issues & tasks** from the specs.
* **Humans oversee + approve**, ensuring compliance and context alignment.

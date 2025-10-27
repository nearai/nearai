# NEAR AI Hub (Deprecated)

!!! warning "DEPRECATED"
    This project is **deprecated**. Server components will be shut down on **October 31, 2025**.

## Deprecation FAQ

!!! question "Why deprecate NEAR AI Agent Framework and Developer Hub?"
    As AI agents have become more popular and more advanced, they've also become more integrated into 'regular' software. There's not that much need (or demand) anymore for a special hosted framework for chat-based AI agents. More often, we're seeing agentic workflows integrated into new or existing applications. For that, existing frameworks like LangChain, AutoGen, and many others are more than sufficient.

!!! question "What's NEAR AI doing?"
    [NEAR AI](https://near.ai/) has built a new platform for private & confidential AI, consisting of:
    
    * NEAR AI Private Chat ([https://private.near.ai/](https://private.near.ai/))
    * NEAR AI Cloud ([https://cloud.near.ai/](https://cloud.near.ai/))
    
    These new products are in active development and as of October 2025 they have not been publicly launched yet; we are disclosing them to the NEAR AI community to maintain service continuity and show you what's coming soon.

!!! question "What will happen to the NEAR AI Developer Hub?"
    The NEAR AI Developer Hub at [https://app.near.ai/](https://app.near.ai/) will shut down on October 31, 2025 and replaced with this notice. After that date, all agents, threads, models, vector stores, datasets, and evaluations will be unavailable. We will delete all user-specific data pertaining to threads, logins, environment variables, secrets, vector stores, and evaluations shortly after the website shuts down. Most agent code and datasets have always been public on NEAR AI; as such, we will keep paying for the S3 bucket that stores that information for the foreseeable future, and can serve individual requests for that data at our discretion upon request.

!!! question "What will happen to my NEAR AI agents?"
    When the NEAR AI Hub goes offline on October 31, 2025, you'll lose access to your agents. Please use the [`nearai registry download`](agents/registry.md#downloading-an-agent) command or the "Export" button to download a copy of your agent code. From there, we recommend adapting it into the AI framework of your choice and hosting it using the infrastructure of your choice. Please reach out on [the NEAR AI Telegram group](https://t.me/nearaialpha) if you'd like migration advice, as we've been working with many users to help migrate their agents to other frameworks.

!!! question "What will happen to NEAR AI inference/completions API?"
    The old NEAR AI completions APIs will go offline on October 31, 2025. We recommend [NEAR AI Cloud](./cloud/get-started.md), our new, fully private & confidential AI API, with a similar OpenAI-compatible API. NEAR AI Cloud is in active alpha development and as of October 2025 has not been publicly launched yet; we are disclosing it to the NEAR AI community to maintain service continuity and show you what's coming soon.
    
    If you urgently need production-ready AI services in advance of the NEAR AI Cloud launch, we also like:
    
    * [Fireworks AI](https://fireworks.ai/), which was powering NEAR AI Hub
    * [RedPill](https://redpill.ai/), another confidential AI API

!!! question "Who can I contact for more information or complaints?"
    We're available on [the NEAR AI Telegram group](https://t.me/nearaialpha).

---

## About NEAR AI Hub (Historical Reference)

Welcome! [NEAR AI](https://near.ai) was a toolkit to help build, measure, and deploy AI systems focused on [agents](./agents/quickstart.md).

Driven by one of the minds behinds **TensorFlow** and the **Transformer Architecture**, NEAR AI put you back in control. Your data stays yours, and your AI works for you, with no compromises on privacy or ownership.

---

<div class="grid cards" markdown>

-   :material-robot-happy: __NEAR AI Agents__

    ---

    Autonomous system that can interact with you and use
    tools to solve tasks

    <span style="display: flex; justify-content: space-between;">
    [:material-clock-fast: Quickstart](./agents/quickstart.md)
    [:material-file-chart: Registry](./agents/registry.md)
    [:material-tools: Tools](./agents/env/tools.md)
    </span>

-   :material-tooltip-text: __AI Models__

    ---

    Best in class AI models that you can use and fine-tune to solve
    your tasks

    <span style="display: flex; justify-content: space-between;">
    [:material-chart-areaspline: Benchmarks](./models/benchmarks_and_evaluations.md)
    [:material-tune: Fine-Tuning](./models/fine_tuning.md)
    </span>


-   :material-web: __Developer Hub__ :octicons-link-external-16:

    ---

    NEAR AI developer hub where you can discover and deploy agents, datasets, and models with ease. 

    <span style="display: flex; justify-content: space-between;">
    [:material-robot-happy: Agents](https://app.near.ai/agents)
    [:material-cogs: Models](https://app.near.ai/models)
    [:material-database: Datasets](https://app.near.ai/agents)
    </span>

-   :material-lightbulb-group: __Community__ :octicons-link-external-16:

    ---

    Join our community! Get help and contribute to the future of AI

    [:simple-telegram: Community](https://t.me/nearaialpha)

</div>

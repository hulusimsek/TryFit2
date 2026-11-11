
# AGENTS.md

## Project
TryFitNext is a new, independent AI-powered 2D virtual try-on project.
The old TryFit repository is reference material only. Never modify it.

## Architecture
- Backend: .NET 9 Web API.
- AI inference: Python worker.
- Frontend and Chrome extension are separate clients.
- AI inference must run on a remote GPU in production.
- Do not make the backend depend on a local GPU.
- Prioritize photorealistic 2D try-on. Do not introduce 3D mannequin workflows.
- Follow Clean Architecture principles in the .NET backend.
- Keep business logic independent of infrastructure and external frameworks.
- Enforce dependency direction: dependencies must point inward toward the Domain layer.
- Keep clear boundaries between Domain, Application, Infrastructure, and API/Presentation layers.
- The Domain layer must not depend on other application layers or infrastructure.
- The Application layer should contain use cases, business workflows, interfaces, and application-level abstractions.
- The Infrastructure layer should implement interfaces defined by inner layers.
- The API layer should handle HTTP concerns and delegate business operations to the Application layer.
- Keep the Python AI worker independently deployable and communicate with the backend through clearly defined contracts.

## Clean Architecture Guidelines
- Prefer simple, maintainable, and testable solutions.
- Apply SOLID principles where they provide practical value.
- Use Dependency Injection for managing dependencies.
- Depend on abstractions rather than concrete infrastructure implementations.
- Keep controllers thin. Do not put business logic in controllers.
- Use DTOs for communication across application boundaries.
- Do not expose Domain entities directly through API responses.
- Keep validation close to the relevant application use cases.
- Use clear and explicit interfaces.
- Avoid circular dependencies between projects.
- Do not introduce unnecessary abstractions, interfaces, repositories, factories, or design patterns.
- Do not overengineer simple features.
- Do not create extra layers or projects without a concrete architectural reason.
- Prefer composition over inheritance when appropriate.

## Important Constraints
- Budget is very limited during development.
- Prefer free and open-source tools.
- Never provision paid cloud resources or services without explicit approval.
- Do not add fake, placeholder, or simulated functionality and present it as working.
- Do not claim a try-on model works until it has been tested with real clothing images.
- Preserve user privacy. Never expose one user's photos or generated results to another user.

## Working Rules
- Before changing code, inspect only the files relevant to the task.
- For large tasks, first provide a short implementation plan and wait for approval.
- For small, clearly defined tasks, implement directly.
- Do not rewrite unrelated files or refactor unrelated modules.
- Avoid adding dependencies unless they are necessary.
- Reuse existing project conventions.
- Maintain Clean Architecture boundaries when adding or modifying code.
- Do not move business logic into infrastructure or presentation layers.
- Run relevant tests and builds after changes.
- If a test cannot be run, explain why.
- Never delete or overwrite user work without permission.
- At the start of a new task or session, check `docs/progress.md` to understand the current project status and next steps.
- Do not re-analyze the entire project when continuing existing work. Inspect only files relevant to the current task.
- After completing a task, update `docs/progress.md` with a concise summary of genuinely completed work.
- Clearly record incomplete work and the next logical step. Never mark unfinished work as completed.
- Do not rewrite the entire progress file. Preserve its existing history and structure; update only the relevant sections.

## Communication
- Be concise and explain important decisions.
- Report exactly which files were changed.
- Clearly distinguish completed work from suggestions.
- Do not repeat the entire project architecture in every response.

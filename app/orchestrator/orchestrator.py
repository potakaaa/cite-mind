from __future__ import annotations

import time
from typing import Any

from app.agents.base_agent import AgentExecutionError
from app.agents.critic_agent import CriticAgent
from app.agents.research_reader_agent import ResearchReaderAgent
from app.agents.writer_agent import WriterAgent
from app.orchestrator.pipeline import PipelineDefinition, get_pipeline_map
from app.orchestrator.task_router import TaskRouter, UnsupportedTaskTypeError
from app.orchestrator.task_schema import StepMeta, TaskInput, TaskResult, TaskType
from app.utils.logging import WorkflowActivityLogger, get_logger, log_failure


class PipelineValidationError(RuntimeError):
    """Raised when a pipeline step fails validation/execution."""


class Orchestrator:
    """Controls which agents run and in what order for each workflow."""

    def __init__(
        self,
        research_reader: ResearchReaderAgent | None = None,
        critic: CriticAgent | None = None,
        writer: WriterAgent | None = None,
        router: TaskRouter | None = None,
        activity_logger: WorkflowActivityLogger | None = None,
    ) -> None:
        self.logger = get_logger("app.orchestrator")
        self.activity_logger = activity_logger
        self.router = router or TaskRouter()
        self.pipelines = get_pipeline_map()
        self.agents = {
            "research_reader": research_reader or ResearchReaderAgent(),
            "critic": critic or CriticAgent(),
            "writer": writer or WriterAgent(),
        }

    def run(self, payload: TaskInput | dict[str, Any]) -> TaskResult:
        try:
            task_input = payload if isinstance(payload, TaskInput) else TaskInput.model_validate(payload)
        except ValueError as exc:
            log_failure(self.logger, "task_input_validation", exc)
            raise

        route = self.router.route(task_input.task_type)
        pipeline = self.pipelines.get(route.pipeline_name)
        if pipeline is None:
            exc = UnsupportedTaskTypeError(
                f"No pipeline configured for route '{route.pipeline_name}'"
            )
            log_failure(self.logger, "pipeline_route_validation", exc, route=route.pipeline_name)
            raise exc

        return self._execute_pipeline(task_input=task_input, pipeline=pipeline)

    def _execute_pipeline(self, task_input: TaskInput, pipeline: PipelineDefinition) -> TaskResult:
        pipeline_start = time.perf_counter()
        context: dict[str, Any] = {
            "paper_text": task_input.paper_text,
            "writer_mode": pipeline.writer_mode,
            "task_type": task_input.task_type.value,
            "user_metadata": dict(task_input.metadata),
        }
        step_meta: list[StepMeta] = []

        if self.activity_logger is not None:
            self.activity_logger.workflow_started(
                pipeline_name=pipeline.name,
                task_type=task_input.task_type.value,
            )

        for step in pipeline.steps:
            start = time.perf_counter()
            try:
                self.logger.info(
                    "Pipeline '%s' starting step '%s' with agent '%s'",
                    pipeline.name,
                    step.name,
                    step.agent_key,
                )
                agent = self.agents[step.agent_key]
                if self.activity_logger is not None:
                    self.activity_logger.agent_started(
                        agent.name,
                        step_name=step.name,
                        pipeline_name=pipeline.name,
                    )
                step_input = step.input_builder(context)
                output = agent.run(
                    provider=task_input.provider,
                    task_type=task_input.task_type.value,
                    **step_input,
                )
                context[step.output_key] = output

                duration_ms = int((time.perf_counter() - start) * 1000)
                step_meta.append(
                    StepMeta(
                        step_name=step.name,
                        agent=agent.name,
                        status="ok",
                        duration_ms=duration_ms,
                        output_keys=[step.output_key],
                    )
                )
                if self.activity_logger is not None:
                    self.activity_logger.agent_finished(
                        agent.name,
                        step_name=step.name,
                        pipeline_name=pipeline.name,
                        duration_ms=duration_ms,
                    )
                self.logger.info(
                    "Pipeline '%s' finished step '%s' in %sms",
                    pipeline.name,
                    step.name,
                    step_meta[-1].duration_ms,
                )
            except (AgentExecutionError, KeyError, TypeError, ValueError) as exc:
                agent_name = (
                    self.agents.get(step.agent_key).name
                    if step.agent_key in self.agents
                    else step.agent_key
                )
                step_meta.append(
                    StepMeta(
                        step_name=step.name,
                        agent=agent_name,
                        status="failed",
                        duration_ms=int((time.perf_counter() - start) * 1000),
                        error=str(exc),
                    )
                )
                if self.activity_logger is not None:
                    self.activity_logger.agent_failed(
                        agent_name,
                        step_name=step.name,
                        pipeline_name=pipeline.name,
                        error=exc,
                    )
                log_failure(
                    self.logger,
                    "pipeline_step",
                    exc,
                    pipeline=pipeline.name,
                    step=step.name,
                    agent=step.agent_key,
                )
                raise PipelineValidationError(
                    f"Pipeline '{pipeline.name}' stopped at step '{step.name}': {exc}"
                ) from exc

        final_output = context.get("final_output")
        if not isinstance(final_output, str) or not final_output.strip():
            exc = PipelineValidationError(
                f"Pipeline '{pipeline.name}' finished without a valid final_output."
            )
            log_failure(self.logger, "pipeline_output_validation", exc, pipeline=pipeline.name)
            raise exc

        intermediate: dict[str, Any] = {}
        if "study" in context:
            intermediate["study"] = context["study"].model_dump()
        if "critique" in context:
            intermediate["critique"] = context["critique"].model_dump()

        intermediate["pipeline"] = pipeline.name
        intermediate["writer_mode"] = pipeline.writer_mode
        intermediate["input_metadata"] = dict(task_input.metadata)

        if self.activity_logger is not None:
            self.activity_logger.workflow_finished(
                pipeline_name=pipeline.name,
                duration_ms=int((time.perf_counter() - pipeline_start) * 1000),
            )

        return TaskResult(
            task_type=task_input.task_type,
            final_output=final_output,
            intermediate=intermediate,
            steps=step_meta,
        )


def run_task(task_type: TaskType | str, paper_text: str, provider: str | None = None) -> TaskResult:
    """Convenience helper for one-shot orchestrator calls."""

    normalized_task_type = task_type if isinstance(task_type, TaskType) else TaskType(task_type)
    orchestrator = Orchestrator()
    return orchestrator.run(
        TaskInput(task_type=normalized_task_type, paper_text=paper_text, provider=provider)
    )

import functools
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from nearai.agents.agent import Agent


class AnalyticsWrapper:
    """Wrapper that tracks method calls and latencies for any client object."""

    def __init__(self, client: Any, client_name: str, analytics_collector: "AnalyticsCollector"):  # noqa: D107
        self._client = client
        self._client_name = client_name
        self._analytics_collector = analytics_collector

        # Store original client for direct access if needed
        self.__dict__["_client"] = client
        self.__dict__["_client_name"] = client_name
        self.__dict__["_analytics_collector"] = analytics_collector

    def __getattr__(self, name: str) -> Any:
        """Intercept attribute access to wrap methods or return original attributes."""
        attr = getattr(self._client, name)

        if callable(attr):
            # Wrap callable methods
            return self._wrap_method(attr, name)
        else:
            # For non-callable attributes that are objects, wrap them but give them access to root client
            if hasattr(attr, "__dict__") and not isinstance(attr, (str, int, float, bool, type(None))):
                nested_client_name = f"{self._client_name}.{name}"
                return AnalyticsWrapper(attr, nested_client_name, self._analytics_collector)
            else:
                # Return simple attributes unwrapped
                return attr

    def _wrap_method(self, method: Any, method_name: str):
        """Wrap a method to track calls and latency."""

        @functools.wraps(method)
        def wrapper(*args, **kwargs):
            full_method_name = f"{self._client_name}.{method_name}"
            start_time = time.time()

            try:
                result = method(*args, **kwargs)
                end_time = time.time()
                latency_ms = (end_time - start_time) * 1000

                self._analytics_collector.record_api_call(
                    method_name=full_method_name, latency_ms=latency_ms, success=True
                )

                return result
            except Exception as e:
                end_time = time.time()
                latency_ms = (end_time - start_time) * 1000

                self._analytics_collector.record_api_call(
                    method_name=full_method_name, latency_ms=latency_ms, success=False, error=str(e)
                )

                raise

        return wrapper


class RunnerMetrics:
    """Runner Metrics."""

    def __init__(self):  # noqa: D107
        self.start_time = time.time()
        self.latency_ms = None

    def ongoing(self) -> bool:  # noqa: D102
        return self.latency_ms is None

    def notify_of_next_step(self, cur_time: Optional[float] = None):  # noqa: D102
        if self.ongoing():
            if not cur_time:
                cur_time = time.time()
            self.latency_ms = (cur_time - self.start_time) * 1000


class EnvInitMetrics:
    """Environment Init Metrics."""

    def __init__(self):  # noqa: D107
        self.start_time = time.time()
        self.latency_ms = None
        self.num_api_calls = 0

    def ongoing(self) -> bool:  # noqa: D102
        return self.latency_ms is None

    def notify_of_next_step(self, cur_time: Optional[float] = None):  # noqa: D102
        if self.ongoing():
            if not cur_time:
                cur_time = time.time()
            self.latency_ms = (cur_time - self.start_time) * 1000


class AnalyticsCollector:
    """Collects and manages analytics data for agent runs."""

    def __init__(self, agent: Agent, debug_mode: bool, env_init_metrics: EnvInitMetrics, upload_entry_fn=None):  # noqa: D107
        self._agent = agent
        self._debug_mode = debug_mode
        self._upload_entry_fn = upload_entry_fn
        self.env_init_metrics = env_init_metrics

        # Track API calls: {method_name: [call_data, ...]}
        self.api_calls: Dict[str, List[Dict[str, Any]]] = {}
        # Track other metrics
        self.custom_metrics: Dict[str, Any] = {}

    def init_env_run_metrics(self, runner_metrics: Optional[RunnerMetrics]):  # noqa: D102
        self.start_time = time.time()
        self.start_time_utc = datetime.now(timezone.utc)
        self.start_time_local = datetime.now()
        self.api_calls = {}
        self.custom_metrics = {}
        self.runner_metrics = runner_metrics
        if self.runner_metrics:
            self.runner_metrics.notify_of_next_step(self.start_time)
        self.env_init_metrics.notify_of_next_step(self.start_time)

    def record_api_call(self, method_name: str, latency_ms: float, success: bool, error: Optional[str] = None):
        """Record an API call with its metrics."""
        if method_name not in self.api_calls:
            self.api_calls[method_name] = []

        self.api_calls[method_name].append(
            {"timestamp": time.time(), "latency_ms": latency_ms, "success": success, "error": error}
        )
        if self.env_init_metrics.ongoing():
            self.env_init_metrics.num_api_calls += 1

    def add_custom_metric(self, key: str, value: Any, description: str):
        """Add a custom metric."""
        self.custom_metrics[key] = {"value": value, "description": description}

    def _get_agent_metadata(self) -> Dict[str, Any]:
        """Extract metadata about the agent and run environment."""
        try:
            agent_metadata = self._agent.metadata
            return {
                "agent_full_name": self._agent.get_full_name(),
                "agent_namespace": self._agent.namespace,
                "agent_name": self._agent.name,
                "agent_version": self._agent.version,
                "model": self._agent.model,
                "model_provider": self._agent.model_provider,
                "model_temperature": self._agent.model_temperature,
                "model_max_tokens": self._agent.model_max_tokens,
                "framework": agent_metadata.get("details", {}).get("agent", {}).get("framework", "minimal"),
                "local": self._agent.is_local,
            }
        except Exception as e:
            return {"agent_metadata_error": str(e)}

    def generate_metrics(self) -> Dict[str, Any]:
        """Generate the final metrics structure."""
        end_time = time.time()
        end_time_utc = datetime.now(timezone.utc)
        end_time_local = datetime.now()

        # Build metadata
        metadata = {
            # Time information
            "start_env_run_time_utc": self.start_time_utc.isoformat(),
            "end_env_run_time_utc": end_time_utc.isoformat(),
            "start_env_run_time_local": self.start_time_local.isoformat(),
            "end_env_run_time_local": end_time_local.isoformat(),
            "debug_mode": self._debug_mode,
        }
        metadata.update(self._get_agent_metadata())

        total_env_run_time_ms = (end_time - self.start_time) * 1000
        # Build metrics
        metrics = {
            "performance/latency/total_env_run_ms": {
                "value": total_env_run_time_ms,
                "description": "Total agent run time in milliseconds, not including any initialization",
            }
        }

        env_init_latency_ms = self.env_init_metrics.latency_ms
        metrics["performance/latency/env_init_latency_ms"] = {
            "value": env_init_latency_ms,
            "description": "Environment initialization time",
        }
        env_init_percentage = (env_init_latency_ms / (env_init_latency_ms + total_env_run_time_ms)) * 100
        metrics["performance/env_init_time_percentage"] = {
            "value": round(env_init_percentage, 2),
            "description": "env_init_latency/(env_init_latency+env_run_time)",
        }

        if self.runner_metrics:
            runner_latency_ms = self.runner_metrics.latency_ms
            metrics["performance/latency/runner_latency_ms"] = {
                "value": runner_latency_ms,
                "description": "Runner start time.",
            }
            runner_percentage = (runner_latency_ms / (runner_latency_ms + total_env_run_time_ms)) * 100
            metrics["performance/runner_time_percentage"] = {
                "value": round(runner_percentage, 2),
                "description": "runner_latency/(runner_latency+env_run_time)",
            }

        total_init_and_env_run_time_ms = total_env_run_time_ms
        if self.runner_metrics:
            # Environment init time is included in runner time.
            total_init_and_env_run_time_ms += runner_latency_ms
        else:
            total_init_and_env_run_time_ms += env_init_latency_ms
        metrics["performance/latency/total_init_and_env_run_ms"] = {
            "value": total_init_and_env_run_time_ms,
            "description": "Total agent init and run time in milliseconds, including runner start time",
        }

        # Add API call metrics
        total_api_calls = 0
        total_api_latency = 0
        total_completion_api_latency = 0
        total_successful_calls = 0
        total_failed_calls = 0
        all_errors = []
        error_summary: dict[str, Any] = {}

        if self.env_init_metrics.num_api_calls > 0:
            self.add_custom_metric(
                "api_calls/env_init/count", self.env_init_metrics.num_api_calls, "Num api calls during Environment init"
            )

        for method_name, calls in self.api_calls.items():
            call_count = len(calls)
            successful_calls = len([c for c in calls if c["success"]])
            failed_calls = call_count - successful_calls
            total_latency = sum(c["latency_ms"] for c in calls)
            avg_latency = total_latency / call_count if call_count > 0 else 0
            min_latency = min(c["latency_ms"] for c in calls) if call_count > 0 else 0
            max_latency = max(c["latency_ms"] for c in calls) if call_count > 0 else 0

            # Collect errors for this method
            method_errors = [c["error"] for c in calls if c["error"] is not None]
            all_errors.extend(method_errors)

            # Count error types for this method
            method_error_counts: dict[str, Any] = {}
            for error in method_errors:
                error_type = (
                    type(error).__name__
                    if hasattr(error, "__class__")
                    else str(error).split(":")[0]
                    if ":" in str(error)
                    else "UnknownError"
                )
                method_error_counts[error_type] = method_error_counts.get(error_type, 0) + 1
                error_summary[error_type] = error_summary.get(error_type, 0) + 1

            # Clean method name for metrics key (replace dots with underscores)
            clean_method_name = method_name.replace(".", "_")
            completion_call = "_completion" in clean_method_name
            base_key = f"api_calls/{clean_method_name}"

            # Update totals
            total_api_calls += call_count
            total_api_latency += total_latency
            if completion_call:
                total_completion_api_latency += total_latency
            total_successful_calls += successful_calls
            total_failed_calls += failed_calls

            metrics[f"{base_key}/count"] = {"value": call_count, "description": f"Number of calls to {method_name}"}

            metrics[f"{base_key}/successful_count"] = {
                "value": successful_calls,
                "description": f"Number of successful calls to {method_name}",
            }

            metrics[f"{base_key}/failed_count"] = {
                "value": failed_calls,
                "description": f"Number of failed calls to {method_name}",
            }

            metrics[f"{base_key}/total_latency_ms"] = {
                "value": total_latency,
                "description": f"Total latency for all calls to {method_name} in milliseconds",
            }

            metrics[f"{base_key}/avg_latency_ms"] = {
                "value": round(avg_latency, 2),
                "description": f"Average latency for calls to {method_name} in milliseconds",
            }

            metrics[f"{base_key}/min_latency_ms"] = {
                "value": round(min_latency, 2),
                "description": f"Minimum latency for calls to {method_name} in milliseconds",
            }

            metrics[f"{base_key}/max_latency_ms"] = {
                "value": round(max_latency, 2),
                "description": f"Maximum latency for calls to {method_name} in milliseconds",
            }

            # Add error metrics for this method if there are any errors
            if method_errors:
                metrics[f"{base_key}/errors/total_count"] = {
                    "value": len(method_errors),
                    "description": f"Total number of errors for {method_name}",
                }

                # Add error type breakdown for this method
                for error_type, count in method_error_counts.items():
                    safe_error_type = error_type.replace(".", "_").replace(" ", "_")
                    metrics[f"{base_key}/errors/by_type/{safe_error_type}"] = {
                        "value": count,
                        "description": f"Number of {error_type} errors for {method_name}",
                    }

                # Add sample error messages (first 3 unique errors)
                unique_errors = list(set(method_errors))[:3]
                for i, error in enumerate(unique_errors):
                    error_msg = str(error)[:200] + ("..." if len(str(error)) > 200 else "")  # Truncate long errors
                    metrics[f"{base_key}/errors/samples/error_{i + 1}"] = {
                        "value": error_msg,
                        "description": f"Sample error message {i + 1} for {method_name}",
                    }

        # Add summary metrics
        metrics["api_calls/summary/total_calls"] = {
            "value": total_api_calls,
            "description": "Total number of API calls made",
        }

        metrics["api_calls/summary/total_successful_calls"] = {
            "value": total_successful_calls,
            "description": "Total number of successful API calls",
        }

        metrics["api_calls/summary/total_failed_calls"] = {
            "value": total_failed_calls,
            "description": "Total number of failed API calls",
        }

        metrics["api_calls/summary/total_api_latency_ms"] = {
            "value": round(total_api_latency, 2),
            "description": "Total latency for all API calls in milliseconds",
        }

        if total_api_calls > 0:
            metrics["api_calls/summary/avg_api_latency_ms"] = {
                "value": round(total_api_latency / total_api_calls, 2),
                "description": "Average latency per API call in milliseconds",
            }

            metrics["api_calls/summary/success_rate"] = {
                "value": round(total_successful_calls / total_api_calls, 4),
                "description": "Success rate of API calls (0.0 to 1.0)",
            }

            metrics["api_calls/summary/failure_rate"] = {
                "value": round(total_failed_calls / total_api_calls, 4),
                "description": "Failure rate of API calls (0.0 to 1.0)",
            }

        # Add error summary metrics
        if all_errors:
            metrics["errors/summary/total_error_count"] = {
                "value": len(all_errors),
                "description": "Total number of errors across all API calls",
            }

            metrics["errors/summary/unique_error_count"] = {
                "value": len(set(all_errors)),
                "description": "Number of unique error messages",
            }

            # Add error type summary
            for error_type, count in error_summary.items():
                safe_error_type = error_type.replace(".", "_").replace(" ", "_")
                metrics[f"errors/summary/by_type/{safe_error_type}"] = {
                    "value": count,
                    "description": f"Total number of {error_type} errors across all methods",
                }

            # Add most common errors (top 5)
            most_common_errors = sorted(error_summary.items(), key=lambda x: x[1], reverse=True)[:5]
            for i, (error_type, count) in enumerate(most_common_errors):
                safe_error_type = error_type.replace(".", "_").replace(" ", "_")
                metrics[f"errors/summary/most_common/rank_{i + 1}"] = {
                    "value": f"{error_type} ({count} occurrences)",
                    "description": f"#{i + 1} most common error type",
                }

            # Add sample of unique error messages (first 5)
            unique_error_samples = list(set(all_errors))[:5]
            for i, error in enumerate(unique_error_samples):
                error_msg = str(error)[:300] + ("..." if len(str(error)) > 300 else "")  # Truncate very long errors
                metrics[f"errors/summary/samples/error_{i + 1}"] = {
                    "value": error_msg,
                    "description": f"Sample error message #{i + 1}",
                }
        else:
            metrics["errors/summary/total_error_count"] = {
                "value": 0,
                "description": "Total number of errors across all API calls",
            }

        # Calculate API percentage
        if total_env_run_time_ms > 0:
            api_percentage = (total_api_latency / total_env_run_time_ms) * 100
            metrics["performance/api_time_percentage"] = {
                "value": round(api_percentage, 2),
                "description": "total_api_latency/total_env_run_time",
            }
            completion_api_percentage = (total_completion_api_latency / total_env_run_time_ms) * 100
            metrics["performance/completion_api_time_percentage"] = {
                "value": round(completion_api_percentage, 2),
                "description": "total_completion_api_latency/total_env_run_time",
            }

        # Add custom metrics
        metrics.update(self.custom_metrics)

        return {"metadata": metadata, "metrics": metrics}

    def flush_to_file(self, log_dir: Path):
        """Write metrics to the logs/metrics.json file."""
        try:
            metrics_data = self.generate_metrics()

            # Ensure logs directory exists
            log_dir.mkdir(parents=True, exist_ok=True)

            # Write to metrics.json
            metrics_file = log_dir / "metrics.json"
            with open(metrics_file, "w") as f:
                json.dump(metrics_data, f, indent=2)

        except Exception as e:
            print(f"Failed to write analytics metrics: {e}")

    def upload(self, thread_dir: Path):
        """Upload analytics to registry."""
        import shutil

        log_dir = thread_dir / "logs"
        try:
            shutil.rmtree(log_dir)
        except Exception:
            pass
        self.flush_to_file(log_dir)

        if not self._upload_entry_fn:
            print("Upload function not available for analytics entry upload")
            return

        if self._debug_mode:
            for log_file in thread_dir.glob("*_log.txt"):
                log_filename = log_file.name
                source_path = thread_dir / log_filename
                dest_path = log_dir / log_filename
                try:
                    shutil.copy2(source_path, dest_path)
                except Exception as e:
                    print(f"Failed to copy {log_filename}: {e}")

        # Create logs name using agent name and timestamp
        agent_name = self._agent.get_full_name()
        timestamp = self.start_time_utc.strftime("%Y%m%d_%H%M%S")
        # Create a clean name for the logs entry
        # Format: logs_{agent_name}_{timestamp}
        logs_name = f"logs_{agent_name}_{timestamp}"
        logs_name = re.sub(r"[^a-zA-Z0-9_\-.]", "_", logs_name)
        logs_description = f"Analytics and logs for {agent_name} run at {self.start_time_utc.isoformat()}"

        metadata_path = log_dir / "metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(
                {
                    "name": logs_name,
                    "version": "0.0.1",
                    "description": logs_description,
                    "category": "logs",
                    "tags": [],
                    "details": {"private_source": True},
                    "show_entry": True,
                },
                f,
                indent=2,
            )

        self._upload_entry_fn(log_dir)


def create_analytics_wrapper(client: Any, client_name: str, analytics_collector: AnalyticsCollector) -> Any:
    """Create an analytics wrapper for a client."""
    return AnalyticsWrapper(client, client_name, analytics_collector)

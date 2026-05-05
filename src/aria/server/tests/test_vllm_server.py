"""Tests for VllmServerManager in server/vllm.py."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from aria.server.vllm import VllmServerManager


class TestBuildVllmCmd:
    """Tests for VllmServerManager._build_vllm_cmd()."""

    def setup_method(self):
        with patch("aria.server.vllm.load_state", return_value={}):
            self.manager = VllmServerManager()

    def test_basic_cmd_structure(self):
        """Command must include required vLLM entrypoint arguments."""
        cmd = self.manager._build_vllm_cmd(
            model_path="BAAI/bge-m3",
            port=9090,
            role="chat",
        )
        assert "-m" in cmd
        assert "vllm.entrypoints.openai.api_server" in cmd
        assert "--model" in cmd
        assert "BAAI/bge-m3" in cmd
        assert "--port" in cmd
        assert "9090" in cmd
        assert "--api-key" in cmd
        assert "sk-aria" in cmd

    def test_embed_task_flag(self):
        """Embeddings server should use --runner pooling --convert embed."""
        cmd = self.manager._build_vllm_cmd(
            model_path="BAAI/bge-m3",
            port=9092,
            role="embeddings",
            task="embed",
        )
        assert "--runner" in cmd
        assert "pooling" in cmd
        assert "--convert" in cmd
        assert "embed" in cmd

    def test_quantization_flag(self):
        """GPTQ quantization should auto-upgrade to gptq_marlin."""
        cmd = self.manager._build_vllm_cmd(
            model_path="/data/models/chat",
            port=9090,
            role="chat",
            quantization="gptq",
        )
        assert "--quantization" in cmd
        assert "gptq_marlin" in cmd

    def test_gptq_forces_float16_dtype(self):
        """GPTQ quantization should force --dtype float16 when dtype is auto."""
        cmd = self.manager._build_vllm_cmd(
            model_path="/data/models/chat",
            port=9090,
            role="chat",
            quantization="gptq",
            dtype="auto",
        )
        dtype_idx = cmd.index("--dtype")
        assert cmd[dtype_idx + 1] == "float16"

    def test_gptq_preserves_explicit_dtype(self):
        """GPTQ quantization should not override an explicit dtype."""
        cmd = self.manager._build_vllm_cmd(
            model_path="/data/models/chat",
            port=9090,
            role="chat",
            quantization="gptq",
            dtype="float16",
        )
        dtype_idx = cmd.index("--dtype")
        assert cmd[dtype_idx + 1] == "float16"

    def test_quantization_not_added_when_none(self):
        """No --quantization flag when quantization is None."""
        cmd = self.manager._build_vllm_cmd(
            model_path="BAAI/bge-m3",
            port=9090,
            role="chat",
            quantization=None,
        )
        assert "--quantization" not in cmd

    def test_tensor_parallel_flag(self):
        """Tensor parallel size > 1 should add --tensor-parallel-size."""
        cmd = self.manager._build_vllm_cmd(
            model_path="/data/models/chat",
            port=9090,
            role="chat",
            tensor_parallel_size=2,
        )
        assert "--tensor-parallel-size" in cmd
        assert "2" in cmd

    def test_no_tensor_parallel_for_single_gpu(self):
        """No --tensor-parallel-size flag for single GPU."""
        cmd = self.manager._build_vllm_cmd(
            model_path="/data/models/chat",
            port=9090,
            role="chat",
            tensor_parallel_size=1,
        )
        assert "--tensor-parallel-size" not in cmd

    def test_chat_template_not_added_for_embed(self):
        """Chat template should NOT be added for embedding task."""
        cmd = self.manager._build_vllm_cmd(
            model_path="BAAI/bge-m3",
            port=9092,
            role="embeddings",
            task="embed",
            chat_template_file="/path/to/template.jinja",
        )
        assert "--chat-template" not in cmd


class TestBuildRerankCmd:
    """Tests for VllmServerManager._build_rerank_cmd()."""

    def setup_method(self):
        with patch("aria.server.vllm.load_state", return_value={}):
            self.manager = VllmServerManager()

    def test_rerank_cmd_uses_aria_module(self):
        """Rerank command should use aria.server.rerank module."""
        cmd = self.manager._build_rerank_cmd(
            model_path="BAAI/bge-reranker-v2-m3",
            port=9093,
        )
        assert "aria.server.rerank" in cmd
        assert "--model" in cmd
        assert "BAAI/bge-reranker-v2-m3" in cmd
        assert "--port" in cmd
        assert "9093" in cmd


class TestStopAll:
    """Tests for VllmServerManager.stop_all()."""

    def setup_method(self):
        with patch("aria.server.vllm.load_state", return_value={}):
            self.manager = VllmServerManager()

    def test_stop_all_calls_stop_process(self):
        """stop_all() should call stop_process for each tracked PID."""
        self.manager._pids = {"chat": 1234, "embeddings": 5678}

        with (
            patch("aria.server.vllm.is_process_running", return_value=True),
            patch("aria.server.vllm.stop_process") as mock_stop,
            patch("aria.server.vllm.clear_state"),
        ):
            self.manager.stop_all()

        assert mock_stop.call_count == 2

    def test_stop_all_clears_pids(self):
        """stop_all() should clear the PID dict after stopping."""
        self.manager._pids = {"chat": 1234}

        with (
            patch("aria.server.vllm.is_process_running", return_value=True),
            patch("aria.server.vllm.stop_process"),
            patch("aria.server.vllm.clear_state"),
        ):
            self.manager.stop_all()

        assert self.manager._pids == {}

    def test_stop_all_skips_dead_processes(self):
        """stop_all() should not call stop_process for already-dead processes."""
        self.manager._pids = {"chat": 9999}

        with (
            patch("aria.server.vllm.is_process_running", return_value=False),
            patch("aria.server.vllm.stop_process") as mock_stop,
            patch("aria.server.vllm.clear_state"),
        ):
            self.manager.stop_all()

        mock_stop.assert_not_called()

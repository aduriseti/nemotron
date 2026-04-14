import pytest
from unittest.mock import patch
import push_notebook
import push_validation

@patch("push_notebook.push_notebook_to_kaggle")
def test_push_notebook_gpu(mock_push):
    push_notebook.push_notebook()
    
    # Check that push_notebook_to_kaggle was called
    mock_push.assert_called_once()
    
    # Get the keyword arguments passed to the mock
    _, kwargs = mock_push.call_args
    metadata = kwargs.get("metadata")
    
    assert metadata is not None, "Metadata was not passed to push_notebook_to_kaggle"
    assert metadata.get("machine_shape") == "NvidiaRtxPro6000", "Incorrect or missing machine_shape in notebook_tinker metadata"

@patch("push_validation.push_notebook_to_kaggle")
def test_push_validation_gpu(mock_push):
    push_validation.push_validation()
    
    # Check that push_notebook_to_kaggle was called
    mock_push.assert_called_once()
    
    # Get the keyword arguments passed to the mock
    _, kwargs = mock_push.call_args
    metadata = kwargs.get("metadata")
    
    assert metadata is not None, "Metadata was not passed to push_notebook_to_kaggle"
    assert metadata.get("machine_shape") == "NvidiaRtxPro6000", "Incorrect or missing machine_shape in adapter-validation-notebook metadata"

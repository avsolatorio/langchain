"""Loader that loads data from JSON."""
import json
from pathlib import Path
from typing import Callable, Dict, List, Union

from langchain.docstore.document import Document
from langchain.document_loaders.base import BaseLoader


class JSONLoader(BaseLoader):
    """Loads a JSON file and references a jq schema provided to load the text into
    documents.

    Example:
        [{"text": ...}, {"text": ...}, {"text": ...}] -> schema = .[].text
        {"key": [{"text": ...}, {"text": ...}, {"text": ...}]} -> schema = .key[].text
        ["", "", ""] -> schema = .[]
    """

    def __init__(
        self,
        file_path: Union[str, Path],
        jq_schema: str,
        content_key: str = None,
        metadata_func: Callable[Dict, Dict] = None,
    ):
        """Initialize the JSONLoader.

        Args:
            file_path (Union[str, Path]): The path to the JSON file.
            jq_schema (str): The jq schema to use to extract the data or text from the JSON.
            content_key (str): The key to use to extract the content from the JSON if the jq_schema results to a list of objects (dict).
            metadata_func (Callable[Dict, Dict]): A function that takes in the JSON object extracted by the jq_schema and the default metadata and returns a dict of the updated metadata.
        """
        try:
            import jq  # noqa:F401
        except ImportError:
            raise ValueError(
                "jq package not found, please install it with " "`pipenv install jq`"
            )

        self.file_path = Path(file_path).resolve()
        self._jq_schema = jq.compile(jq_schema)
        self._content_key = content_key
        self._metadata_func = metadata_func

    def load(self) -> List[Document]:
        """Load and return documents from the JSON file."""

        data = self._jq_schema.input(json.loads(self.file_path.read_text()))

        # Perform some validation
        # This is not a perfect validation, but it should catch most cases
        # and prevent the user from getting a cryptic error later on.
        if self._content_key is not None:
            sample = data.first()
            assert isinstance(sample, dict)
            assert sample.get(self._content_key) is not None

            if self._metadata_func is not None:
                assert isinstance(self._metadata_func(sample, {}), dict)

        docs = []

        for i, sample in enumerate(data, 1):
            metadata = dict(
                source=str(self.file_path),
                seq_num=i,
            )

            if self._content_key is not None:
                text = sample.get(self._content_key)
                if self._metadata_func is not None:
                    # We pass in the metadata dict to the metadata_func
                    # so that the user can customize the default metadata
                    # based on the content of the JSON object.
                    metadata = self._metadata_func(sample, metadata)
            else:
                text = sample

            # In case the text is None, set it to an empty string
            text = text or ""

            docs.append(Document(page_content=text, metadata=metadata))

        return docs
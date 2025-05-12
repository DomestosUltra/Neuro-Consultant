import weaviate
import logging

from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class WeaviateClient:
    """
    Client for working with Weaviate vector database
    """

    def __init__(self, url: str, api_key: Optional[str] = None):
        """
        Initialize Weaviate client

        Args:
            url: Weaviate instance URL (e.g., "http://localhost:8080")
            api_key: Optional API key for authentication
        """
        try:
            logger.info(f"API key: {api_key}")

            self.client = weaviate.connect_to_local(
                host="weaviate",
                port=8080,
                grpc_port=50051,
                headers={
                    "X-OpenAI-Api-Key": (
                        api_key if api_key else None
                    )  # For text2vec-openai module
                },
            )

            logger.info(
                f"Weaviate client successfully initialized with URL: {url}"
            )

            # Check connection
            self._check_connection()
        except Exception as e:
            logger.error(f"Error initializing Weaviate client: {e}")
            # Initialize empty client to avoid attribute access errors
            self.client = None
            raise

    def _check_connection(self):
        """Check connection to Weaviate and log version information"""
        try:
            # In v4 API, we use .get_meta() method directly on the client
            meta = self.client.get_meta()
            logger.info(f"Connected to Weaviate: {meta['version']}")
        except Exception as e:
            logger.error(f"Error connecting to Weaviate: {e}")
            raise

    def get_schema(self) -> Dict[str, Any]:
        """Get the current schema from Weaviate"""
        try:
            # Get all collections in v4 API
            collections = self.client.collections.get_all()

            # Transform to a format compatible with the old API to support existing code
            schema = {"classes": []}

            for collection in collections:
                class_data = {
                    "class": collection.name,
                    "description": collection.config.description,
                    "properties": [],
                }

                # Add properties
                for prop in collection.properties:
                    property_data = {
                        "name": prop.name,
                        "description": prop.description,
                        "dataType": [self._convert_data_type(prop.data_type)],
                    }
                    class_data["properties"].append(property_data)

                schema["classes"].append(class_data)

            return schema
        except Exception as e:
            logger.error(f"Error getting Weaviate schema: {e}")
            return {"classes": []}

    def _convert_data_type(self, data_type) -> str:
        """Convert Weaviate data type to string representation"""
        data_type_mapping = {
            "text": "text",
            "int": "int",
            "number": "number",
            "boolean": "boolean",
            "date": "date",
        }
        return data_type_mapping.get(str(data_type).lower(), "text")

    def create_class(self, class_obj: Dict[str, Any]) -> bool:
        """
        Create a new class in Weaviate

        Args:
            class_obj: Class definition according to Weaviate schema

        Returns:
            bool: Success status
        """
        try:
            class_name = class_obj.get("class")

            # Create collection with configuration
            properties = class_obj.get("properties", [])

            # Create collection
            collection = self.client.collections.create(
                name=class_name,
                description=class_obj.get("description", ""),
                vectorizer_config=weaviate.classes.config.Configure.Vectorizer.text2vec_openai(),
            )

            # Add properties
            for prop in properties:
                prop_name = prop.get("name")
                prop_data_type = prop.get("dataType", ["text"])[0]

                # Handle different data types
                if prop_data_type == "text":
                    collection.properties.create(
                        name=prop_name,
                        description=prop.get("description", ""),
                        data_type=weaviate.classes.config.DataType.TEXT,
                    )
                elif prop_data_type == "string":
                    collection.properties.create(
                        name=prop_name,
                        description=prop.get("description", ""),
                        data_type=weaviate.classes.config.DataType.TEXT,
                    )
                elif prop_data_type == "int":
                    collection.properties.create(
                        name=prop_name,
                        description=prop.get("description", ""),
                        data_type=weaviate.classes.config.DataType.INT,
                    )
                elif prop_data_type == "boolean":
                    collection.properties.create(
                        name=prop_name,
                        description=prop.get("description", ""),
                        data_type=weaviate.classes.config.DataType.BOOLEAN,
                    )
                elif prop_data_type == "number":
                    collection.properties.create(
                        name=prop_name,
                        description=prop.get("description", ""),
                        data_type=weaviate.classes.config.DataType.NUMBER,
                    )

            logger.info(f"Created class: {class_name}")
            return True
        except Exception as e:
            logger.error(f"Error creating Weaviate class: {e}")
            return False

    def add_object(
        self,
        class_name: str,
        properties: Dict[str, Any],
        vector: Optional[List[float]] = None,
    ) -> Optional[str]:
        """
        Add an object to Weaviate

        Args:
            class_name: Name of the class to add the object to
            properties: Object properties
            vector: Optional pre-computed vector

        Returns:
            str: UUID of created object or None if failed
        """
        try:
            # Get the collection
            collection = self.client.collections.get(class_name)

            # Create object with or without vector
            if vector:
                result = collection.data.insert(
                    properties=properties, vector=vector
                )
            else:
                result = collection.data.insert(properties=properties)

            return result
        except Exception as e:
            logger.error(f"Error adding object to Weaviate: {e}")
            return None

    def search_objects(
        self,
        class_name: str,
        query_vector: Optional[List[float]] = None,
        query_text: Optional[str] = None,
        properties: Optional[List[str]] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Search for objects in Weaviate

        Args:
            class_name: Class to search in
            query_vector: Vector to search by (for vector search)
            query_text: Text to search by (for text search)
            properties: List of properties to return
            limit: Maximum number of results

        Returns:
            List of objects matching the search criteria
        """
        try:
            collection = self.client.collections.get(class_name)

            # If properties are not specified, get all
            if not properties:
                schema_props = [prop.name for prop in collection.properties]
                properties = schema_props

            query_builder = collection.query

            if query_vector:
                # Vector search
                query_builder = query_builder.near_vector(
                    vector=query_vector, limit=limit
                )
            elif query_text:
                # Text search using text2vec-openai
                query_builder = query_builder.near_text(
                    query=query_text, limit=limit
                )
            else:
                # Get all objects with limit
                query_builder = query_builder.with_limit(limit)

            # Add properties to return
            result = (
                query_builder.with_additional(["id", "distance"])
                .with_fields(properties)
                .do()
            )

            # Format the results to match the expected output format
            objects = []
            if hasattr(result, "objects"):
                for obj in result.objects:
                    formatted_obj = {
                        "id": obj.uuid,
                        "properties": obj.properties,
                    }
                    if hasattr(obj, "metadata") and hasattr(
                        obj.metadata, "distance"
                    ):
                        formatted_obj["distance"] = obj.metadata.distance
                    objects.append(formatted_obj)

            return objects

        except Exception as e:
            logger.error(f"Error searching Weaviate: {e}")
            return []

    def delete_object(self, class_name: str, uuid: str) -> bool:
        """Delete object by UUID"""
        try:
            collection = self.client.collections.get(class_name)
            collection.data.delete_by_id(uuid)
            return True
        except Exception as e:
            logger.error(f"Error deleting object from Weaviate: {e}")
            return False

    def batch_import(
        self, class_name: str, objects: List[Dict[str, Any]]
    ) -> bool:
        """
        Import a batch of objects

        Args:
            class_name: Name of the class to add objects to
            objects: List of objects to add

        Returns:
            bool: Success status
        """
        try:
            collection = self.client.collections.get(class_name)

            # Use the batch context manager to efficiently add objects
            with collection.batch.dynamic() as batch:
                for obj in objects:
                    properties = obj.get(
                        "properties", obj
                    )  # Support both formats
                    batch.add_object(properties=properties)

            return True
        except Exception as e:
            logger.error(f"Error batch importing to Weaviate: {e}")
            return False

    def close(self):
        """Close the Weaviate client connection"""
        if self.client:
            self.client.close()
            logger.info("Weaviate client connection closed")

    def clear_collection(self, class_name: str) -> bool:
        """
        Clear all objects from a collection

        Args:
            class_name: Name of the collection to clear

        Returns:
            bool: Success status
        """
        try:
            collection = self.client.collections.get(class_name)
            collection.data.delete_all()
            logger.info(f"Cleared all objects from collection: {class_name}")
            return True
        except Exception as e:
            logger.error(f"Error clearing collection {class_name}: {e}")
            return False

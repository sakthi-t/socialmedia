import chromadb
from chromadb.api import ClientAPI
from chromadb.api.models.Collection import Collection
import os
from dotenv import load_dotenv
import uuid
import json
from datetime import datetime

load_dotenv()

class ChromaManager:
    def __init__(self):
        self.api_key = os.getenv("CHROMA_API_KEY")
        self.tenant = os.getenv("CHROMA_TENANT")
        self.database = os.getenv("CHROMA_DATABASE")
        self.client = None
        self.collection = None

    def get_client(self) -> ClientAPI:
        """Initialize and return Chroma Cloud client"""
        if not self.client:
            self.client = chromadb.CloudClient(
                api_key=self.api_key,
                tenant=self.tenant,
                database=self.database
            )
        return self.client

    def get_collection(self) -> Collection:
        """Get or create the chat collection"""
        if not self.collection:
            client = self.get_client()
            self.collection = client.get_or_create_collection(
                name="swift_chat_history",
                metadata={"description": "Chat history for Swift AI assistant"}
            )
        return self.collection

    def add_conversation(self, user_id: str, session_id: str, user_message: str, ai_response: str) -> str:
        """Add conversation to Chroma Cloud"""
        collection = self.get_collection()
        doc_id = str(uuid.uuid4())

        # Create metadata
        metadata = {
            "user_id": str(user_id),
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat(),
            "type": "conversation"
        }

        # Create document content
        document = {
            "user": user_message,
            "assistant": ai_response
        }

        collection.add(
            ids=[doc_id],
            documents=[json.dumps(document)],
            metadatas=[metadata]
        )

        return doc_id

    def delete_conversation(self, doc_id: str):
        """Delete a conversation from Chroma Cloud"""
        try:
            collection = self.get_collection()
            collection.delete(ids=[doc_id])
            return True
        except Exception as e:
            print(f"Error deleting from Chroma: {e}")
            return False

    def search_conversations(self, user_id: str, query: str, limit: int = 5):
        """Search user's conversation history"""
        collection = self.get_collection()

        results = collection.query(
            query_texts=[query],
            n_results=limit,
            where={"user_id": str(user_id)}
        )

        return results

    def get_user_sessions(self, user_id: str):
        """Get all session IDs for a user"""
        collection = self.get_collection()

        # Get all documents for the user
        results = collection.get(
            where={"user_id": str(user_id)},
            include=["metadatas"]
        )

        # Extract unique session IDs
        sessions = {}
        for metadata in results.get('metadatas', []):
            session_id = metadata.get('session_id')
            timestamp = metadata.get('timestamp')
            if session_id and session_id not in sessions:
                sessions[session_id] = timestamp

        # Sort by most recent
        sorted_sessions = sorted(
            sessions.items(),
            key=lambda x: x[1],
            reverse=True
        )

        return [session[0] for session in sorted_sessions]

    def delete_all_user_conversations(self, user_id: str):
        """Delete all conversations for a user"""
        try:
            collection = self.get_collection()

            # Get all document IDs for the user
            results = collection.get(
                where={"user_id": str(user_id)},
                include=["metadatas"]
            )

            if results.get('ids'):
                collection.delete(ids=results['ids'])
                return True
        except Exception as e:
            print(f"Error deleting user conversations: {e}")
        return False

# Global instance
chroma_manager = ChromaManager()
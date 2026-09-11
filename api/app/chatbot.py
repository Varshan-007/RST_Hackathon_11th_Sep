import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from .neo4j_client import neo4j_client

logger = logging.getLogger("api.chatbot")

class ChatbotEngine:
    def process_question(self, question: str) -> Dict[str, Any]:
        """
        Process a natural language question, generate grounded Cypher, execute against Neo4j,
        and return the structured response adhering to the contract.
        """
        q_raw = question.strip()
        q_lower = q_raw.lower()

        # Step 1: Check if graph has any data
        schema = neo4j_client.get_schema_summary()
        row_count = schema.get("row_count", 0)
        properties = schema.get("properties", [])
        sample_values = schema.get("sample_values", {})

        if row_count == 0:
            cypher = "MATCH (d:Dataset) RETURN count(d) AS dataset_count"
            result = neo4j_client.execute_query(cypher)
            return {
                "answer": "I don't have that in the data because no dataset has been uploaded yet. Please upload a CSV first.",
                "cypher": cypher,
                "result": result,
                "grounded": False
            }

        # Step 2: Match Intent & Generate Cypher
        cypher, template_type, match_meta = self._generate_cypher(q_raw, q_lower, properties, sample_values)

        if not cypher:
            # Ungrounded question that doesn't match dataset schema
            props_str = ", ".join(properties) if properties else "none"
            fallback_cypher = "MATCH (r:Row) RETURN keys(r) AS properties LIMIT 1"
            res = neo4j_client.execute_query(fallback_cypher)
            return {
                "answer": f"I don't have that in the data. The uploaded dataset contains {row_count} rows with properties: {props_str}.",
                "cypher": fallback_cypher,
                "result": res,
                "grounded": False
            }

        # Step 3: Execute Cypher against Neo4j
        try:
            result = neo4j_client.execute_query(cypher)
        except Exception as e:
            logger.error(f"Error executing Cypher query '{cypher}': {e}")
            return {
                "answer": f"I encountered an error querying the graph: {str(e)}",
                "cypher": cypher,
                "result": [],
                "grounded": False
            }

        # Step 4: Phrase Grounded Answer
        answer, is_grounded = self._phrase_answer(q_raw, template_type, match_meta, result, properties)

        return {
            "answer": answer,
            "cypher": cypher,
            "result": result,
            "grounded": is_grounded
        }

    def _find_matching_column(self, text: str, properties: List[str]) -> Optional[str]:
        """Find the property name mentioned in text or closest match."""
        # Clean text
        words = re.findall(r'\w+', text.lower())
        for prop in properties:
            if prop.lower() in words or prop.lower() in text.lower():
                return prop
        # Also check common synonyms
        synonyms = {
            "dept": "department",
            "group": "department" if "department" in properties else ("group" if "group" in properties else None),
            "groups": "department" if "department" in properties else ("group" if "group" in properties else None),
            "title": "role" if "role" in properties else ("title" if "title" in properties else None),
            "location": "city" if "city" in properties else ("location" if "location" in properties else None),
            "user": "name" if "name" in properties else None,
            "person": "name" if "name" in properties else None,
            "state": "status" if "status" in properties else ("state" if "state" in properties else None)
        }
        for syn, target in synonyms.items():
            if target and syn in words and target in properties:
                return target
        return None

    def _find_matching_value(self, text: str, sample_values: Dict[str, List[str]]) -> Optional[Tuple[str, str]]:
        """Search across sample values to find (column, value) match."""
        for col, values in sample_values.items():
            for val in values:
                # Check for exact word or phrase match
                pattern = r'\b' + re.escape(val.lower()) + r'\b'
                if re.search(pattern, text.lower()):
                    return col, val
        return None

    def _generate_cypher(self, q_raw: str, q_lower: str, properties: List[str], sample_values: Dict[str, List[str]]) -> Tuple[Optional[str], str, Dict[str, Any]]:
        meta: Dict[str, Any] = {}

        # 1. Schema / Columns inspection
        if any(p in q_lower for p in ["what columns", "list columns", "show columns", "show schema", "what fields", "list fields", "attributes", "properties"]):
            cypher = "MATCH (r:Row) WITH keys(r) AS k UNWIND k AS prop WITH DISTINCT prop WHERE NOT prop IN ['dataset_id', 'row_index'] RETURN collect(prop) AS columns"
            return cypher, "SCHEMA", meta

        # 2. Dataset information / uploads
        if any(p in q_lower for p in ["dataset info", "what dataset", "which dataset", "when was it uploaded", "upload date", "filename"]):
            cypher = "MATCH (d:Dataset) RETURN d.id AS dataset_id, d.filename AS filename, toString(d.uploaded_at) AS uploaded_at, d.row_count AS row_count"
            return cypher, "DATASET_INFO", meta

        # 3. Graph structure / relationships
        if any(p in q_lower for p in ["how are rows connected", "relationships", "graph structure", "connections in graph"]):
            cypher = "MATCH (d:Dataset)-[rel]->(r:Row) RETURN type(rel) AS relationship, count(rel) AS count"
            return cypher, "RELATIONSHIPS", meta

        # 4. Row by specific index / ID
        row_match = re.search(r'\brow\s*(?:index|number|#)?\s*(\d+)\b', q_lower)
        if row_match:
            row_idx = int(row_match.group(1))
            meta["row_index"] = row_idx
            cypher = f"MATCH (r:Row {{row_index: {row_idx}}}) RETURN r LIMIT 1"
            return cypher, "ROW_LOOKUP", meta

        id_match = re.search(r'\b(?:id|employee id|record id)\s*(?:is|=|:)?\s*(\d+)\b', q_lower)
        if id_match and "id" in properties:
            rec_id = id_match.group(1)
            meta["id"] = rec_id
            cypher = f"MATCH (r:Row) WHERE toString(r.id) = '{rec_id}' RETURN r LIMIT 1"
            return cypher, "ID_LOOKUP", meta

        # 5. Group by / Breakdown distribution
        if any(p in q_lower for p in ["breakdown", "per ", "distribution", "group by", "count by"]):
            matched_col = self._find_matching_column(q_lower, properties)
            if matched_col:
                meta["column"] = matched_col
                cypher = f"MATCH (r:Row) WHERE r.{matched_col} IS NOT NULL RETURN toString(r.{matched_col}) AS {matched_col}, count(r) AS count ORDER BY count DESC"
                return cypher, "BREAKDOWN", meta

        # 6. Aggregations (Average, Max, Min, Sum)
        agg_match = None
        if "average" in q_lower or "avg" in q_lower or "mean" in q_lower:
            agg_match = "avg"
        elif "maximum" in q_lower or "max" in q_lower or "highest" in q_lower:
            agg_match = "max"
        elif "minimum" in q_lower or "min" in q_lower or "lowest" in q_lower:
            agg_match = "min"
        elif "sum" in q_lower or "total salary" in q_lower:
            agg_match = "sum"

        if agg_match:
            matched_col = self._find_matching_column(q_lower, properties)
            if matched_col:
                meta["agg"] = agg_match
                meta["column"] = matched_col
                cypher = f"MATCH (r:Row) WHERE r.{matched_col} IS NOT NULL RETURN {agg_match}(toFloat(r.{matched_col})) AS {agg_match}_{matched_col}"
                return cypher, "AGGREGATION", meta

        # 7. Distinct / Unique values for a column
        if any(p in q_lower for p in ["unique", "distinct", "list all", "what are the", "show all", "all categories"]):
            matched_col = self._find_matching_column(q_lower, properties)
            if matched_col:
                meta["column"] = matched_col
                cypher = f"MATCH (r:Row) WHERE r.{matched_col} IS NOT NULL RETURN DISTINCT toString(r.{matched_col}) AS {matched_col} ORDER BY {matched_col}"
                return cypher, "DISTINCT_VALUES", meta

        # 8. Value match & filtering (e.g. "How many rows belong to the Billing group?" or "count active employees")
        val_match = self._find_matching_value(q_lower, sample_values)
        if val_match:
            col, val = val_match
            meta["column"] = col
            meta["value"] = val
            
            # Check if asking for count or list of rows
            is_count = any(p in q_lower for p in ["how many", "count", "number of", "total"])
            if is_count:
                cypher = f"MATCH (r:Row) WHERE toLower(toString(r.{col})) = '{val.lower()}' RETURN count(r) AS count"
                return cypher, "FILTER_COUNT", meta
            else:
                cypher = f"MATCH (r:Row) WHERE toLower(toString(r.{col})) = '{val.lower()}' RETURN r LIMIT 10"
                return cypher, "FILTER_ROWS", meta

        # 9. Quoted value filter: e.g. where status = 'inactive'
        quoted_match = re.search(r"['\"]([^'\"]+)['\"]", q_raw)
        if quoted_match:
            val = quoted_match.group(1).strip()
            matched_col = self._find_matching_column(q_lower, properties)
            if matched_col:
                meta["column"] = matched_col
                meta["value"] = val
                is_count = any(p in q_lower for p in ["how many", "count", "number of", "total"])
                if is_count:
                    cypher = f"MATCH (r:Row) WHERE toLower(toString(r.{matched_col})) = '{val.lower()}' RETURN count(r) AS count"
                    return cypher, "FILTER_COUNT", meta
                else:
                    cypher = f"MATCH (r:Row) WHERE toLower(toString(r.{matched_col})) = '{val.lower()}' RETURN r LIMIT 10"
                    return cypher, "FILTER_ROWS", meta

        # 10. Generic filter matching pattern: "where [col] is [word]"
        pattern_filter = re.search(r'(?:where|with|in|for)\s+([a-zA-Z_]+)\s+(?:is|=|as)?\s+([a-zA-Z0-9_-]+)', q_lower)
        if pattern_filter:
            cand_col = pattern_filter.group(1)
            cand_val = pattern_filter.group(2)
            matched_col = self._find_matching_column(cand_col, properties)
            if matched_col:
                meta["column"] = matched_col
                meta["value"] = cand_val
                is_count = any(p in q_lower for p in ["how many", "count", "number of", "total"])
                if is_count:
                    cypher = f"MATCH (r:Row) WHERE toLower(toString(r.{matched_col})) = '{cand_val.lower()}' RETURN count(r) AS count"
                    return cypher, "FILTER_COUNT", meta
                else:
                    cypher = f"MATCH (r:Row) WHERE toLower(toString(r.{matched_col})) = '{cand_val.lower()}' RETURN r LIMIT 10"
                    return cypher, "FILTER_ROWS", meta

        # 11. Total rows count (checked after specific value/column filters)
        if any(p in q_lower for p in ["how many rows", "count rows", "total rows", "total records", "number of rows", "how many records", "dataset size", "how many items", "how many entries"]):
            cypher = "MATCH (r:Row) RETURN count(r) AS count"
            return cypher, "TOTAL_COUNT", meta

        # If none matched, return None for ungrounded answer
        return None, "UNGROUNDED", meta

    def _phrase_answer(self, q_raw: str, template_type: str, meta: Dict[str, Any], result: List[Dict[str, Any]], properties: List[str]) -> Tuple[str, bool]:
        if not result:
            col = meta.get("column", "")
            val = meta.get("value", "")
            if col and val:
                return f"No rows found where {col} = '{val}'.", True
            return "I don't have that in the data.", False

        if template_type == "TOTAL_COUNT":
            count = result[0].get("count", 0)
            return f"There are {count} total rows in the dataset.", True

        elif template_type == "FILTER_COUNT":
            col = meta.get("column", "group")
            val = meta.get("value", "")
            count = result[0].get("count", 0)
            if count == 0:
                return f"There are 0 rows where {col} = '{val}'.", True
            return f"There are {count} rows where {col} = '{val}'.", True

        elif template_type == "DISTINCT_VALUES":
            col = meta.get("column", "column")
            values = [str(r.get(col)) for r in result if r.get(col) is not None]
            val_str = ", ".join(values[:25])
            if len(values) > 25:
                val_str += f", and {len(values) - 25} more"
            return f"The {len(values)} distinct values for '{col}' are: {val_str}.", True

        elif template_type == "BREAKDOWN":
            col = meta.get("column", "column")
            parts = [f"{r.get(col)}: {r.get('count')}" for r in result[:10]]
            return f"Distribution for '{col}': " + ", ".join(parts) + ".", True

        elif template_type == "FILTER_ROWS":
            col = meta.get("column", "column")
            val = meta.get("value", "")
            return f"Found {len(result)} matching rows where {col} = '{val}'.", True

        elif template_type == "AGGREGATION":
            agg = meta.get("agg", "agg")
            col = meta.get("column", "column")
            val = list(result[0].values())[0] if result and result[0] else None
            if val is not None:
                if isinstance(val, float):
                    return f"The {agg} of '{col}' is {val:.2f}.", True
                return f"The {agg} of '{col}' is {val}.", True
            return f"Could not calculate {agg} for column '{col}'.", False

        elif template_type == "ROW_LOOKUP":
            idx = meta.get("row_index")
            row_data = result[0].get("r", {})
            props_str = ", ".join([f"{k}: {v}" for k, v in row_data.items() if k not in ['dataset_id']])
            return f"Row {idx} details: {props_str}", True

        elif template_type == "ID_LOOKUP":
            rec_id = meta.get("id")
            row_data = result[0].get("r", {})
            props_str = ", ".join([f"{k}: {v}" for k, v in row_data.items() if k not in ['dataset_id']])
            return f"Record ID {rec_id} details: {props_str}", True

        elif template_type == "SCHEMA":
            cols = result[0].get("columns", [])
            return f"The dataset contains columns: {', '.join(cols)}.", True

        elif template_type == "DATASET_INFO":
            r = result[0]
            filename = r.get("filename", "unknown")
            dataset_id = r.get("dataset_id", "unknown")
            uploaded_at = r.get("uploaded_at", "unknown")
            row_count = r.get("row_count", 0)
            return f"Dataset '{filename}' (ID: {dataset_id}) has {row_count} rows and was uploaded at {uploaded_at}.", True

        elif template_type == "RELATIONSHIPS":
            rel_types = [f"{r.get('relationship')}: {r.get('count')}" for r in result]
            return f"Graph relationships: {', '.join(rel_types)}.", True

        return "Query executed successfully.", True

chatbot_engine = ChatbotEngine()

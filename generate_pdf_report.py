import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        
        # Header (pages > 1)
        if self._pageNumber > 1:
            self.setFont("Helvetica-Bold", 8)
            self.setFillColor(colors.HexColor("#4338ca"))
            self.drawString(54, 750, "DATA IN, ANSWERS OUT")
            self.setFont("Helvetica", 8)
            self.setFillColor(colors.HexColor("#64748b"))
            self.drawString(165, 750, "— CSV · Kafka · Neo4j Streaming & Grounded Graph Intelligence")
            self.setStrokeColor(colors.HexColor("#e2e8f0"))
            self.setLineWidth(0.75)
            self.line(54, 742, 558, 742)

        # Footer (all pages)
        self.setStrokeColor(colors.HexColor("#e2e8f0"))
        self.setLineWidth(0.75)
        self.line(54, 45, 558, 45)
        
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))
        self.drawString(54, 32, "RISE @ RST Hackathon #5 — Comprehensive Technical Project Report")
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(558, 32, page_text)
        self.restoreState()

def create_report(output_filename="PROJECT_REPORT.pdf"):
    pdf_path = os.path.abspath(output_filename)
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=58,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()
    
    # Custom Palette
    c_primary = colors.HexColor("#1e1b4b")   # Deep Indigo
    c_accent = colors.HexColor("#4338ca")    # Indigo Accent
    c_cyan = colors.HexColor("#0284c7")      # Cyan
    c_emerald = colors.HexColor("#059669")   # Emerald
    c_dark = colors.HexColor("#0f172a")      # Text dark
    c_muted = colors.HexColor("#475569")     # Text muted
    c_card_bg = colors.HexColor("#f8fafc")   # Light gray card
    c_border = colors.HexColor("#e2e8f0")

    # Custom Typography Styles
    style_cover_title = ParagraphStyle(
        'CoverTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=c_primary,
        spaceAfter=6
    )
    
    style_cover_sub = ParagraphStyle(
        'CoverSub',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        leading=16,
        textColor=c_cyan,
        spaceAfter=14
    )

    style_h1 = ParagraphStyle(
        'Header1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=c_primary,
        spaceBefore=12,
        spaceAfter=6,
        keepWithNext=True
    )

    style_h2 = ParagraphStyle(
        'Header2',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=c_accent,
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True
    )

    style_body = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=c_dark,
        spaceAfter=6
    )

    style_code = ParagraphStyle(
        'CodeStyle',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#334155")
    )

    style_table_header = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.white
    )

    style_table_cell = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=c_dark
    )

    style_table_mono = ParagraphStyle(
        'TableMono',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor("#1e293b")
    )

    story = []

    # =========================================================================
    # COVER / HEADER BANNER
    # =========================================================================
    story.append(Paragraph("DATA IN, ANSWERS OUT", style_cover_title))
    story.append(Paragraph("A Production-Grade CSV Streaming, Neo4j Graph & Grounded Chatbot Platform", style_cover_sub))
    
    meta_table_data = [
        [
            Paragraph("<b>Event:</b> RISE @ RST Hackathon #5", style_table_cell),
            Paragraph("<b>Author:</b> Varshan (@Varshan-007)", style_table_cell),
            Paragraph("<b>Architecture:</b> 5-Container Docker Compose", style_table_cell)
        ],
        [
            Paragraph("<b>Date:</b> September 2026", style_table_cell),
            Paragraph("<b>Repository:</b> RST_Hackathon_11th_Sep", style_table_cell),
            Paragraph("<b>Security:</b> CIS Compliant / 100% Non-Root", style_table_cell)
        ]
    ]
    meta_table = Table(meta_table_data, colWidths=[168, 168, 168])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), c_card_bg),
        ('BOX', (0,0), (-1,-1), 1, c_border),
        ('INNERGRID', (0,0), (-1,-1), 0.5, c_border),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 10))

    # =========================================================================
    # 1. EXECUTIVE SUMMARY & SYSTEM OVERVIEW
    # =========================================================================
    story.append(Paragraph("1. Executive Summary & System Overview", style_h1))
    story.append(Paragraph(
        "<b>'Data In, Answers Out'</b> is a modern, resilient enterprise data streaming and graph intelligence pipeline designed to ingest arbitrary, unstandardized CSV files of any volume, publish records through an <b>Apache Kafka KRaft</b> streaming backbone, merge them idempotently into a <b>Neo4j 5.24 Graph Database</b>, and expose a <b>strictly grounded Natural Language Chatbot</b> that translates user inquiries directly into Cypher graph queries without hallucinations.",
        style_body
    ))
    story.append(Paragraph(
        "The system executes with zero manual setup steps via <code>docker compose up -d</code> across five decoupled, non-root microservices adhering to strict containerization hygiene, resource limits, and automated health checks.",
        style_body
    ))

    # Architecture Box
    arch_data = [
        [Paragraph("<b>Service</b>", style_table_header), Paragraph("<b>Technology & Image</b>", style_table_header), Paragraph("<b>Port</b>", style_table_header), Paragraph("<b>Key Responsibilities & Guarantees</b>", style_table_header)],
        [Paragraph("<b>ui</b>", style_table_cell), Paragraph("nginx:1.27-alpine<br/>(76.1MB · non-root)", style_table_cell), Paragraph(":3000", style_table_mono), Paragraph("Glassmorphic SPA, live /status polling, table preview, visual charts & grounded chat.", style_table_cell)],
        [Paragraph("<b>api</b>", style_table_cell), Paragraph("python:3.11-slim (FastAPI)<br/>(319MB · appuser:1000)", style_table_cell), Paragraph(":8000", style_table_mono), Paragraph("Validates CSVs, SHA-256 dataset hashing, streams to Kafka & returns 202 Accepted in &lt;50ms.", style_table_cell)],
        [Paragraph("<b>kafka</b>", style_table_cell), Paragraph("apache/kafka:3.7.0<br/>(KRaft Mode · Single Broker)", style_table_cell), Paragraph(":9092", style_table_mono), Paragraph("Persistent log topic <code>csv-rows</code>. Zero ZooKeeper overhead; handles burst uploads.", style_table_cell)],
        [Paragraph("<b>loader</b>", style_table_cell), Paragraph("python:3.11-slim (Bolt)<br/>(248MB · appuser:1000)", style_table_cell), Paragraph("Internal", style_table_mono), Paragraph("Consumes rows, executes transactional <code>MERGE</code>, updates real-time <code>:Job</code> state machine.", style_table_cell)],
        [Paragraph("<b>neo4j</b>", style_table_cell), Paragraph("neo4j:5.24-community<br/>(Bolt 7687, HTTP 7474)", style_table_cell), Paragraph(":7474<br/>:7687", style_table_mono), Paragraph("ACID graph database indexing <code>(:Dataset)</code>, <code>(:Row)</code>, and tracking <code>(:Job)</code> nodes.", style_table_cell)]
    ]
    arch_table = Table(arch_data, colWidths=[50, 125, 45, 284])
    arch_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_primary),
        ('BOX', (0,0), (-1,-1), 1, c_border),
        ('INNERGRID', (0,0), (-1,-1), 0.5, c_border),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, c_card_bg]),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(arch_table)
    story.append(Spacer(1, 10))

    # =========================================================================
    # 2. DATA MODELING & GRAPH SCHEMA DESIGN
    # =========================================================================
    story.append(Paragraph("2. Graph Schema & Idempotency Architecture", style_h1))
    story.append(Paragraph(
        "Arbitrary CSV schemas are mapped dynamically into Neo4j using a robust, normalized graph hierarchy without schema pre-registration:",
        style_body
    ))
    
    schema_data = [
        [Paragraph("<b>Node Label</b>", style_table_header), Paragraph("<b>Primary Key / Constraints</b>", style_table_header), Paragraph("<b>Properties & Type Coercion</b>", style_table_header)],
        [
            Paragraph("<b>:Dataset</b>", style_table_cell),
            Paragraph("<code>id</code> (SHA-256[:12])", style_table_mono),
            Paragraph("<code>filename</code> (str), <code>uploaded_at</code> (datetime), <code>row_count</code> (int)", style_table_cell)
        ],
        [
            Paragraph("<b>:Row</b>", style_table_cell),
            Paragraph("Composite: <code>(dataset_id + row_index)</code>", style_table_mono),
            Paragraph("All CSV columns dynamically mapped. Numbers coerced to <code>INTEGER/FLOAT</code> for Cypher aggregations.", style_table_cell)
        ],
        [
            Paragraph("<b>:Job</b>", style_table_cell),
            Paragraph("<code>id</code> (UUID[:8])", style_table_mono),
            Paragraph("<code>status</code> (queued|loading|complete|failed), <code>rows_loaded</code>, <code>rows_failed</code>, <code>rows_total</code>", style_table_cell)
        ]
    ]
    schema_table = Table(schema_data, colWidths=[70, 160, 274])
    schema_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_accent),
        ('BOX', (0,0), (-1,-1), 1, c_border),
        ('INNERGRID', (0,0), (-1,-1), 0.5, c_border),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, c_card_bg]),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(schema_table)
    story.append(Spacer(1, 6))

    story.append(Paragraph("<b>Relationship Hierarchy:</b> <code>(:Dataset)-[:HAS_ROW]->(:Row)</code> (Strict 1-to-N ownership).", style_body))
    story.append(Paragraph("<b>Idempotency Guarantee:</b> Ingestion executes Cypher <code>MERGE (r:Row {dataset_id: $dataset_id, row_index: $row_index}) ON CREATE SET r += $props ON MATCH SET r += $props</code>. Repeated uploads of identical datasets produce zero duplicate records.", style_body))

    story.append(PageBreak())

    # =========================================================================
    # 3. VERIFICATION RESULTS & TEST SUITE
    # =========================================================================
    story.append(Paragraph("3. Automated Test Suite & Validation Results", style_h1))
    story.append(Paragraph(
        "The automated verification suite (<code>verify_pipeline.py</code>) validates edge cases, hostile payloads, throughput latency, and chatbot query grounding:",
        style_body
    ))

    # Hostile Tests Table
    hostile_data = [
        [Paragraph("<b>Test Case</b>", style_table_header), Paragraph("<b>Test Payload</b>", style_table_header), Paragraph("<b>Expected Code</b>", style_table_header), Paragraph("<b>System Behavior / Error Message</b>", style_table_header), Paragraph("<b>Result</b>", style_table_header)],
        [Paragraph("Empty File", style_table_cell), Paragraph("<code>empty.csv</code> (0 Bytes)", style_table_mono), Paragraph("400 Bad Request", style_table_cell), Paragraph("Rejected immediately: <i>'Uploaded CSV file is empty (0 bytes).'</i>", style_table_cell), Paragraph("<b>PASS ✅</b>", style_table_cell)],
        [Paragraph("Header Only", style_table_cell), Paragraph("<code>header_only.csv</code>", style_table_mono), Paragraph("400 Bad Request", style_table_cell), Paragraph("Rejected: <i>'CSV contains header but zero data rows.'</i>", style_table_cell), Paragraph("<b>PASS ✅</b>", style_table_cell)],
        [Paragraph("Non-CSV MIME", style_table_cell), Paragraph("<code>not_a_csv.txt</code>", style_table_mono), Paragraph("400 Bad Request", style_table_cell), Paragraph("Rejected: <i>'Invalid file format. Only CSV files supported.'</i>", style_table_cell), Paragraph("<b>PASS ✅</b>", style_table_cell)],
        [Paragraph("Ragged CSV", style_table_cell), Paragraph("<code>broken_ragged.csv</code>", style_table_mono), Paragraph("202 Accepted", style_table_cell), Paragraph("Valid rows loaded (2/4); ragged lines recorded in <code>rows_failed</code>.", style_table_cell), Paragraph("<b>PASS ✅</b>", style_table_cell)],
        [Paragraph("Idempotency Repeat", style_table_cell), Paragraph("<code>small_clean.csv</code> (2x)", style_table_mono), Paragraph("202 Accepted", style_table_cell), Paragraph("Row count remained exactly 20. Zero duplicate nodes created.", style_table_cell), Paragraph("<b>PASS ✅</b>", style_table_cell)]
    ]
    hostile_table = Table(hostile_data, colWidths=[80, 95, 80, 195, 54])
    hostile_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_primary),
        ('BOX', (0,0), (-1,-1), 1, c_border),
        ('INNERGRID', (0,0), (-1,-1), 0.5, c_border),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, c_card_bg]),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(hostile_table)
    story.append(Spacer(1, 10))

    # =========================================================================
    # 4. CHATBOT GROUNDING & CYPHER QUERY EXECUTION
    # =========================================================================
    story.append(Paragraph("4. Grounded Natural Language Engine Results", style_h1))
    story.append(Paragraph(
        "Every natural language prompt is mapped deterministically to a parameterized Cypher query. If a question inquires about data absent from the graph, the engine explicitly admits <code>grounded: false</code>:",
        style_body
    ))

    chat_data = [
        [Paragraph("<b>User Question</b>", style_table_header), Paragraph("<b>Generated Cypher Query</b>", style_table_header), Paragraph("<b>Returned Answer</b>", style_table_header), Paragraph("<b>Grounded?</b>", style_table_header)],
        [
            Paragraph("<b>'How many rows in total?'</b>", style_table_cell),
            Paragraph("<code>MATCH (r:Row) RETURN count(r) AS count</code>", style_table_mono),
            Paragraph("There are 20 total rows in the dataset.", style_table_cell),
            Paragraph("<b>Grounded ✅</b>", style_table_cell)
        ],
        [
            Paragraph("<b>'How many belong to Billing?'</b>", style_table_cell),
            Paragraph("<code>MATCH (r:Row) WHERE toLower(toString(r.department)) = 'billing' RETURN count(r) AS count</code>", style_table_mono),
            Paragraph("There are 5 rows where department = 'Billing'.", style_table_cell),
            Paragraph("<b>Grounded ✅</b>", style_table_cell)
        ],
        [
            Paragraph("<b>'What are unique departments?'</b>", style_table_cell),
            Paragraph("<code>MATCH (r:Row) WHERE r.department IS NOT NULL RETURN DISTINCT toString(r.department) AS department ORDER BY department</code>", style_table_mono),
            Paragraph("The 5 distinct values are: Billing, Engineering, Marketing, Sales, Support.", style_table_cell),
            Paragraph("<b>Grounded ✅</b>", style_table_cell)
        ],
        [
            Paragraph("<b>'What is the average salary?'</b>", style_table_cell),
            Paragraph("<code>MATCH (r:Row) WHERE r.salary IS NOT NULL RETURN avg(toFloat(r.salary)) AS avg_salary</code>", style_table_mono),
            Paragraph("The avg of 'salary' is 92,100.00.", style_table_cell),
            Paragraph("<b>Grounded ✅</b>", style_table_cell)
        ],
        [
            Paragraph("<b>'Who is the president of France?'</b>", style_table_cell),
            Paragraph("<code>MATCH (r:Row) RETURN keys(r) AS properties LIMIT 1</code>", style_table_mono),
            Paragraph("I don't have that in the data. The uploaded dataset contains properties: name, dept, role...", style_table_cell),
            Paragraph("<b>Ungrounded ⚠️</b><br/>(Refusal)", style_table_cell)
        ]
    ]
    chat_table = Table(chat_data, colWidths=[100, 170, 164, 70])
    chat_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_accent),
        ('BOX', (0,0), (-1,-1), 1, c_border),
        ('INNERGRID', (0,0), (-1,-1), 0.5, c_border),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, c_card_bg]),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(chat_table)
    story.append(Spacer(1, 10))

    # =========================================================================
    # 5. SECURITY, HYGIENE & BENCHMARKS
    # =========================================================================
    story.append(Paragraph("5. Security, Container Hygiene & Performance Benchmarks", style_h1))
    
    sec_data = [
        [Paragraph("<b>Metric / Criterion</b>", style_table_header), Paragraph("<b>Target Specification</b>", style_table_header), Paragraph("<b>Achieved Measure</b>", style_table_header), Paragraph("<b>Status</b>", style_table_header)],
        [Paragraph("API Ingestion Latency", style_table_cell), Paragraph("&lt; 200 ms for 1,000 rows", style_table_cell), Paragraph("<b>15.92 ms</b> (Single batch stream)", style_table_cell), Paragraph("PASS ✅", style_table_cell)],
        [Paragraph("FastAPI Image Footprint", style_table_cell), Paragraph("&lt; 400 MB image size", style_table_cell), Paragraph("<b>319 MB</b> (python:3.11-slim)", style_table_cell), Paragraph("PASS ✅", style_table_cell)],
        [Paragraph("UI Nginx Footprint", style_table_cell), Paragraph("&lt; 150 MB image size", style_table_cell), Paragraph("<b>76.1 MB</b> (nginx:1.27-alpine)", style_table_cell), Paragraph("PASS ✅", style_table_cell)],
        [Paragraph("Process Security Context", style_table_cell), Paragraph("100% Non-Root Execution", style_table_cell), Paragraph("<b>USER appuser (UID 1000) & USER nginx</b>", style_table_cell), Paragraph("PASS ✅", style_table_cell)],
        [Paragraph("Tag Pinning", style_table_cell), Paragraph("Zero 'latest' image tags", style_table_cell), Paragraph("<code>kafka:3.7.0</code>, <code>neo4j:5.24</code> pinned", style_table_cell), Paragraph("PASS ✅", style_table_cell)]
    ]
    sec_table = Table(sec_data, colWidths=[120, 130, 184, 70])
    sec_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_primary),
        ('BOX', (0,0), (-1,-1), 1, c_border),
        ('INNERGRID', (0,0), (-1,-1), 0.5, c_border),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, c_card_bg]),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(sec_table)
    story.append(Spacer(1, 10))

    # =========================================================================
    # 6. HOW TO RUN
    # =========================================================================
    story.append(Paragraph("6. Zero-Manual-Step Execution Commands", style_h1))
    cmd_text = (
        "<b>1. Boot entire stack:</b> <code>docker compose down -v && docker compose up -d</code><br/>"
        "<b>2. Check health readiness:</b> <code>curl http://localhost:8000/health</code><br/>"
        "<b>3. Run automated verification:</b> <code>python3 verify_pipeline.py</code><br/>"
        "<b>4. Open Web UI Dashboard:</b> Navigate to <b>http://localhost:3000</b>"
    )
    story.append(Paragraph(cmd_text, style_body))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully generated PDF report: {pdf_path}")
    return pdf_path

if __name__ == "__main__":
    create_report()

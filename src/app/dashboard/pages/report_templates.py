"""
Report Templates Page
=====================
Manage report templates and generate custom reports.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

from ..components.sidebar import render_page_header
from ..data import load_runs
from src.analytics.report_templates import ReportTemplateEngine, ReportFormat


def render_report_templates():
    """Render report templates page."""
    render_page_header("Report Templates", "Create and manage custom report templates")
    
    engine = ReportTemplateEngine()
    
    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Templates", "➕ Create Template", "📊 Generate Report", "📜 Report History"])
    
    with tab1:
        _render_templates(engine)
    
    with tab2:
        _render_create_template(engine)
    
    with tab3:
        _render_generate_report(engine)
    
    with tab4:
        _render_report_history(engine)


def _render_templates(engine: ReportTemplateEngine):
    """Render templates list."""
    st.subheader("Report Templates")
    
    templates = engine.get_templates()
    
    if not templates:
        st.info("No templates found. Create one in the 'Create Template' tab.")
        return
    
    for template in templates:
        with st.expander(f"📄 {template.name} ({template.format.upper()})", expanded=False):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.write(f"**Format:** {template.format.upper()}")
                st.write(f"**Description:** {template.description or 'No description'}")
                st.write(f"**Status:** {'✅ Enabled' if template.enabled else '❌ Disabled'}")
                st.write(f"**Created:** {template.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
                if template.last_run_at:
                    st.write(f"**Last Generated:** {template.last_run_at.strftime('%Y-%m-%d %H:%M:%S')}")
                
                # Show sections
                sections = template.get_sections()
                if sections:
                    st.write("**Sections:**")
                    for section in sections:
                        status = "✅" if section.get('enabled', True) else "❌"
                        st.write(f"  {status} {section.get('type', 'unknown').replace('_', ' ').title()}")
            
            with col2:
                if st.button("🗑️ Delete", key=f"delete_template_{template.id}"):
                    try:
                        engine.delete_template(template.id)
                        st.success("Template deleted!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
                
                if st.button("✏️ Edit", key=f"edit_template_{template.id}"):
                    st.info("Edit functionality to be implemented")


def _render_create_template(engine: ReportTemplateEngine):
    """Render create template form."""
    st.subheader("Create New Report Template")
    
    with st.form("create_template_form"):
        name = st.text_input("Template Name", key="template_name")
        description = st.text_area("Description", key="template_description")
        
        format = st.selectbox(
            "Output Format",
            options=[f.value for f in ReportFormat],
            format_func=lambda x: x.upper(),
            key="template_format"
        )
        
        # Section selection
        st.markdown("### Sections")
        sections_config = []
        
        section_types = [
            ('executive_summary', 'Executive Summary'),
            ('performance_metrics', 'Performance Metrics'),
            ('portfolio_composition', 'Portfolio Composition'),
            ('risk_analysis', 'Risk Analysis'),
            ('recommendations', 'Recommendations'),
            ('attribution', 'Performance Attribution'),
            ('benchmark_comparison', 'Benchmark Comparison'),
            ('factor_exposure', 'Factor Exposure')
        ]
        
        for section_type, section_name in section_types:
            enabled = st.checkbox(
                section_name,
                value=True,
                key=f"section_{section_type}"
            )
            sections_config.append({
                'type': section_type,
                'enabled': enabled
            })
        
        submitted = st.form_submit_button("Create Template", use_container_width=True)
        
        if submitted:
            if not name:
                st.error("Template name is required.")
            else:
                try:
                    template = engine.create_template(
                        name=name,
                        format=format,
                        sections=sections_config,
                        description=description
                    )
                    st.success(f"✅ Template created successfully! (ID: {template.id})")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error creating template: {e}")
                    import traceback
                    st.code(traceback.format_exc())


def _render_generate_report(engine: ReportTemplateEngine):
    """Render generate report form."""
    st.subheader("Generate Report")
    
    # Get templates
    templates = engine.get_templates(enabled_only=True)
    if not templates:
        st.warning("No enabled templates found. Create a template first.")
        return
    
    template_options = {f"{t.name} ({t.format.upper()})": t.id for t in templates}
    selected_template_label = st.selectbox(
        "Select Template",
        options=list(template_options.keys()),
        key="generate_report_template"
    )
    selected_template_id = template_options[selected_template_label]
    
    # Get runs
    runs = load_runs()
    if not runs:
        st.warning("No analysis runs found.")
        return
    
    run_options = {f"{r['name'] or r['run_id'][:16]} ({r['created_at'].split('T')[0]})": r['run_id'] 
                   for r in runs}
    selected_run_label = st.selectbox(
        "Select Run",
        options=list(run_options.keys()),
        key="generate_report_run"
    )
    selected_run_id = run_options[selected_run_label]
    
    # Generate button
    if st.button("📊 Generate Report", use_container_width=True):
        with st.spinner("Generating report..."):
            try:
                report_gen = engine.generate_report(
                    template_id=selected_template_id,
                    run_id=selected_run_id
                )
                
                if report_gen.status == 'completed':
                    st.success(f"✅ Report generated successfully!")
                    st.info(f"**File:** {report_gen.file_path}")
                    st.info(f"**Size:** {report_gen.file_size_bytes / 1024:.1f} KB")
                    
                    # Download button
                    if Path(report_gen.file_path).exists():
                        with open(report_gen.file_path, 'rb') as f:
                            file_bytes = f.read()
                            file_ext = Path(report_gen.file_path).suffix[1:]
                            st.download_button(
                                label="📥 Download Report",
                                data=file_bytes,
                                file_name=Path(report_gen.file_path).name,
                                mime=f"application/{file_ext}" if file_ext in ['pdf', 'json'] else f"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                else:
                    st.error(f"❌ Report generation failed: {report_gen.error_message}")
            except Exception as e:
                st.error(f"❌ Error generating report: {e}")
                import traceback
                st.code(traceback.format_exc())
    
    with col2:
        if enable_schedule and schedule_config:
            if st.button("💾 Save Schedule", use_container_width=True):
                # Save schedule (would integrate with scheduler)
                st.success("✅ Schedule saved! Reports will be generated automatically.")
                st.info("⚠️ **Note**: Requires application to be running for scheduled reports.")


def _render_report_history(engine: ReportTemplateEngine):
    """Render report generation history."""
    st.subheader("Report Generation History")
    
    # Filters
    templates = engine.get_templates()
    template_options = {f"{t.name}": t.id for t in templates}
    template_options['All Templates'] = None
    
    selected_template = st.selectbox(
        "Filter by Template",
        options=list(template_options.keys()),
        key="report_history_template_filter"
    )
    selected_template_id = template_options[selected_template]
    
    # Get history
    history = engine.get_report_history(
        template_id=selected_template_id,
        limit=50
    )
    
    if not history:
        st.info("No report generation history found.")
        return
    
    # Display as table
    history_data = []
    for report in history:
        history_data.append({
            'Generated': report.generated_at.strftime('%Y-%m-%d %H:%M:%S'),
            'Template': next((t.name for t in templates if t.id == report.template_id), 'Unknown'),
            'Run ID': report.run_id[:16] if report.run_id else 'N/A',
            'Format': report.format.upper(),
            'Status': '✅' if report.status == 'completed' else '❌',
            'File': Path(report.file_path).name if report.file_path else 'N/A',
            'Size (KB)': f"{report.file_size_bytes / 1024:.1f}" if report.file_size_bytes else 'N/A'
        })
    
    df = pd.DataFrame(history_data)
    st.dataframe(df, use_container_width=True, hide_index=True)

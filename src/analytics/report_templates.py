"""
Report Templates System
=======================
User-configurable report templates for generating custom reports.
"""

import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
from pathlib import Path

from src.analytics.models import get_db, Base
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship


class ReportFormat(Enum):
    """Report output formats."""
    PDF = "pdf"
    EXCEL = "excel"
    CSV = "csv"
    JSON = "json"
    HTML = "html"


class ReportTemplate(Base):
    """Report template definition."""
    __tablename__ = 'report_templates'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    
    # Template configuration
    format = Column(String(20), default='pdf')  # pdf, excel, csv, json, html
    template_json = Column(Text, nullable=False)  # JSON template definition
    
    # Sections configuration
    sections_json = Column(Text)  # JSON array of section configurations
    
    # Scheduling
    enabled = Column(Boolean, default=True)
    schedule_json = Column(Text)  # JSON for scheduling (cron-like)
    
    # Metadata
    created_by = Column(String(200))
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    last_run_at = Column(DateTime, nullable=True)
    
    # Default template flag
    is_default = Column(Boolean, default=False)
    
    def get_template(self) -> Dict:
        """Get template configuration."""
        return json.loads(self.template_json) if self.template_json else {}
    
    def set_template(self, template: Dict):
        """Set template configuration."""
        self.template_json = json.dumps(template)
    
    def get_sections(self) -> List[Dict]:
        """Get sections configuration."""
        return json.loads(self.sections_json) if self.sections_json else []
    
    def set_sections(self, sections: List[Dict]):
        """Set sections configuration."""
        self.sections_json = json.dumps(sections)
    
    def get_schedule(self) -> Dict:
        """Get schedule configuration."""
        return json.loads(self.schedule_json) if self.schedule_json else {}
    
    def set_schedule(self, schedule: Dict):
        """Set schedule configuration."""
        self.schedule_json = json.dumps(schedule)


class ReportGeneration(Base):
    """Record of generated reports."""
    __tablename__ = 'report_generations'
    
    id = Column(Integer, primary_key=True)
    template_id = Column(Integer, ForeignKey('report_templates.id'), nullable=False, index=True)
    run_id = Column(String(50), ForeignKey('runs.run_id'), nullable=True, index=True)
    
    # Generation details
    format = Column(String(20), nullable=False)
    file_path = Column(String(500), nullable=True)  # Path to generated file
    file_size_bytes = Column(Integer, nullable=True)
    
    # Status
    status = Column(String(20), default='completed')  # completed, failed, in_progress
    error_message = Column(Text, nullable=True)
    
    # Metadata
    generated_at = Column(DateTime, default=datetime.now, index=True)
    generated_by = Column(String(200))
    
    # Template snapshot (in case template changes)
    template_snapshot_json = Column(Text)
    
    def get_template_snapshot(self) -> Dict:
        """Get template snapshot."""
        return json.loads(self.template_snapshot_json) if self.template_snapshot_json else {}
    
    def set_template_snapshot(self, snapshot: Dict):
        """Set template snapshot."""
        self.template_snapshot_json = json.dumps(snapshot)


class ReportTemplateEngine:
    """Engine for generating reports from templates."""
    
    def __init__(self, db_path: str = "data/analysis.db"):
        """Initialize template engine."""
        self.db = get_db(db_path)
    
    def create_template(
        self,
        name: str,
        format: str = 'pdf',
        sections: Optional[List[Dict]] = None,
        description: Optional[str] = None,
        created_by: Optional[str] = None
    ) -> ReportTemplate:
        """
        Create a new report template.
        
        Args:
            name: Template name
            format: Output format (pdf, excel, csv, json, html)
            sections: List of section configurations
            description: Template description
            created_by: Creator identifier
            
        Returns:
            Created ReportTemplate
        """
        session = self.db.get_session()
        try:
            template = ReportTemplate(
                name=name,
                format=format,
                description=description,
                created_by=created_by
            )
            
            # Set default template structure
            default_template = {
                'title': name,
                'include_cover_page': True,
                'include_table_of_contents': True,
                'page_size': 'letter',
                'orientation': 'portrait',
                'margins': {'top': 0.75, 'bottom': 0.75, 'left': 0.75, 'right': 0.75}
            }
            template.set_template(default_template)
            
            if sections:
                template.set_sections(sections)
            else:
                # Default sections
                template.set_sections([
                    {'type': 'executive_summary', 'enabled': True},
                    {'type': 'performance_metrics', 'enabled': True},
                    {'type': 'portfolio_composition', 'enabled': True},
                    {'type': 'risk_analysis', 'enabled': True},
                    {'type': 'recommendations', 'enabled': True}
                ])
            
            session.add(template)
            session.commit()
            session.refresh(template)
            return template
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
    
    def generate_report(
        self,
        template_id: int,
        run_id: str,
        output_path: Optional[Path] = None,
        generated_by: Optional[str] = None,
        parallel: bool = False
    ) -> ReportGeneration:
        """
        Generate a report from a template.
        
        Args:
            template_id: Template ID
            run_id: Run ID to generate report for
            output_path: Optional output path (if None, uses default location)
            generated_by: Generator identifier
            
        Returns:
            ReportGeneration record
        """
        from src.analytics.analysis_service import AnalysisService
        from src.app.dashboard.export import export_to_pdf, export_to_excel, export_to_csv, export_to_json
        
        session = self.db.get_session()
        try:
            template = session.query(ReportTemplate).filter_by(id=template_id).first()
            if not template:
                raise ValueError(f"Template {template_id} not found")
            
            # Get analysis results
            analysis_service = AnalysisService()
            all_results = {}
            
            # Get all analysis types
            analysis_types = ['attribution', 'benchmark_comparison', 'factor_exposure', 
                            'rebalancing', 'style', 'event_analysis', 'tax_optimization',
                            'monte_carlo', 'turnover_analysis', 'earnings_calendar']
            
            for analysis_type in analysis_types:
                result = analysis_service.get_analysis_result(run_id, analysis_type)
                if result:
                    all_results[analysis_type] = {
                        'results': result.get_results() if hasattr(result, 'get_results') else result.results_json,
                        'summary': result.get_summary() if hasattr(result, 'get_summary') else result.summary_json
                    }
            
            # Get run info
            from src.analytics.models import Run
            run = session.query(Run).filter_by(run_id=run_id).first()
            run_info = run.to_dict() if run else {}
            
            # Determine output path
            if not output_path:
                output_dir = Path("output/reports")
                output_dir.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{template.name.replace(' ', '_')}_{run_id[:16]}_{timestamp}.{template.format}"
                output_path = output_dir / filename
            
            # Generate report based on format
            report_gen = ReportGeneration(
                template_id=template_id,
                run_id=run_id,
                format=template.format,
                status='in_progress',
                generated_by=generated_by
            )
            report_gen.set_template_snapshot(template.get_template())
            session.add(report_gen)
            session.commit()
            
            try:
                if template.format == 'pdf':
                    pdf_bytes = export_to_pdf(all_results, run_info, output_path)
                    report_gen.file_path = str(output_path)
                    report_gen.file_size_bytes = len(pdf_bytes) if isinstance(pdf_bytes, bytes) else output_path.stat().st_size
                elif template.format == 'excel':
                    excel_bytes = export_to_excel(all_results, run_info, output_path)
                    report_gen.file_path = str(output_path)
                    report_gen.file_size_bytes = len(excel_bytes) if isinstance(excel_bytes, bytes) else output_path.stat().st_size
                elif template.format == 'csv':
                    # Export as CSV (simplified - would need custom logic)
                    import pandas as pd
                    df = pd.json_normalize(all_results)
                    df.to_csv(output_path, index=False)
                    report_gen.file_path = str(output_path)
                    report_gen.file_size_bytes = output_path.stat().st_size
                elif template.format == 'json':
                    with open(output_path, 'w') as f:
                        json.dump(all_results, f, indent=2, default=str)
                    report_gen.file_path = str(output_path)
                    report_gen.file_size_bytes = output_path.stat().st_size
                else:
                    raise ValueError(f"Unsupported format: {template.format}")
                
                report_gen.status = 'completed'
                template.last_run_at = datetime.now()
                session.add(template)
                
            except Exception as e:
                report_gen.status = 'failed'
                report_gen.error_message = str(e)
                raise
            finally:
                session.commit()
                session.refresh(report_gen)
            
            return report_gen
            
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
    
    def get_templates(
        self,
        enabled_only: bool = False
    ) -> List[ReportTemplate]:
        """Get all templates."""
        session = self.db.get_session()
        try:
            query = session.query(ReportTemplate)
            if enabled_only:
                query = query.filter_by(enabled=True)
            return query.order_by(ReportTemplate.created_at.desc()).all()
        finally:
            session.close()
    
    def get_template(self, template_id: int) -> Optional[ReportTemplate]:
        """Get a specific template."""
        session = self.db.get_session()
        try:
            return session.query(ReportTemplate).filter_by(id=template_id).first()
        finally:
            session.close()
    
    def update_template(
        self,
        template_id: int,
        name: Optional[str] = None,
        format: Optional[str] = None,
        sections: Optional[List[Dict]] = None,
        template_config: Optional[Dict] = None,
        enabled: Optional[bool] = None
    ) -> ReportTemplate:
        """Update a template."""
        session = self.db.get_session()
        try:
            template = session.query(ReportTemplate).filter_by(id=template_id).first()
            if not template:
                raise ValueError(f"Template {template_id} not found")
            
            if name:
                template.name = name
            if format:
                template.format = format
            if sections is not None:
                template.set_sections(sections)
            if template_config:
                template.set_template(template_config)
            if enabled is not None:
                template.enabled = enabled
            
            template.updated_at = datetime.now()
            session.commit()
            session.refresh(template)
            return template
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
    
    def delete_template(self, template_id: int) -> bool:
        """Delete a template."""
        session = self.db.get_session()
        try:
            template = session.query(ReportTemplate).filter_by(id=template_id).first()
            if template:
                session.delete(template)
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
    
    def get_report_history(
        self,
        template_id: Optional[int] = None,
        run_id: Optional[str] = None,
        limit: int = 100
    ) -> List[ReportGeneration]:
        """Get report generation history."""
        session = self.db.get_session()
        try:
            query = session.query(ReportGeneration)
            
            if template_id:
                query = query.filter_by(template_id=template_id)
            if run_id:
                query = query.filter_by(run_id=run_id)
            
            return query.order_by(ReportGeneration.generated_at.desc()).limit(limit).all()
        finally:
            session.close()

"""
Dashboard service for analytics and reporting
Provides comprehensive dashboard data for different user roles
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, and_, case

from .base import BaseService, ServiceResult, CacheableService
from models.crop_target import CropTarget, CropTargetStatus, Season
from models.user import User, UserRole
from models.audit import AuditLog, AuditAction


class DashboardService(CacheableService[CropTarget]):
    """Comprehensive dashboard analytics service"""
    
    def __init__(self, db_session: Session):
        super().__init__(CropTarget, db_session, cache_ttl=300)  # 5 minutes cache
    
    def get_vo_dashboard(self, user_id: str, filters: Dict[str, Any] = None) -> ServiceResult:
        """
        Generate Village Officer dashboard with personal statistics
        """
        cache_key = self._get_cache_key("vo_dashboard", user_id=user_id, **filters or {})
        cached_data = self._get_cache(cache_key)
        
        if cached_data:
            return ServiceResult.success_result(data=cached_data)
        
        try:
            # Base query for user's crop targets
            base_query = self.db.query(CropTarget).filter(CropTarget.submitted_by == user_id)
            
            # Apply filters
            if filters:
                if filters.get('year'):
                    base_query = base_query.filter(CropTarget.year == filters['year'])
                if filters.get('season'):
                    base_query = base_query.filter(CropTarget.season == Season(filters['season']))
            
            # Summary statistics
            summary_stats = self._get_vo_summary_stats(base_query)
            
            # Status breakdown
            status_breakdown = self._get_status_breakdown(base_query)
            
            # Crop type breakdown
            crop_breakdown = self._get_crop_breakdown(base_query)
            
            # Timeline data
            timeline_data = self._get_timeline_data(base_query)
            
            # Recent activities
            recent_activities = self._get_recent_activities(user_id, limit=10)
            
            # Performance metrics
            performance_metrics = self._get_vo_performance_metrics(base_query)
            
            dashboard_data = {
                "summary": summary_stats,
                "status_breakdown": status_breakdown,
                "crop_breakdown": crop_breakdown,
                "timeline_data": timeline_data,
                "recent_activities": recent_activities,
                "performance_metrics": performance_metrics,
                "generated_at": datetime.utcnow().isoformat()
            }
            
            # Cache the results
            self._set_cache(cache_key, dashboard_data)
            
            return ServiceResult.success_result(data=dashboard_data)
            
        except Exception as e:
            return ServiceResult.error_result(f"Error generating VO dashboard: {str(e)}")
    
    def get_bo_dashboard(self, filters: Dict[str, Any] = None) -> ServiceResult:
        """
        Generate Block Officer dashboard with comprehensive system statistics
        """
        cache_key = self._get_cache_key("bo_dashboard", **filters or {})
        cached_data = self._get_cache(cache_key)
        
        if cached_data:
            return ServiceResult.success_result(data=cached_data)
        
        try:
            # Base query for all crop targets
            base_query = self.db.query(CropTarget)
            
            # Apply filters
            if filters:
                if filters.get('year'):
                    base_query = base_query.filter(CropTarget.year == filters['year'])
                if filters.get('season'):
                    base_query = base_query.filter(CropTarget.season == Season(filters['season']))
                if filters.get('district'):
                    base_query = base_query.filter(CropTarget.district.ilike(f"%{filters['district']}%"))
            
            # Summary statistics
            summary_stats = self._get_bo_summary_stats(base_query)
            
            # Approval workflow statistics
            approval_stats = self._get_approval_workflow_stats(base_query)
            
            # Geographic breakdown
            geographic_breakdown = self._get_geographic_breakdown(base_query)
            
            # User activity statistics
            user_activity_stats = self._get_user_activity_stats()
            
            # System performance metrics
            system_metrics = self._get_system_performance_metrics()
            
            # Trend analysis
            trend_analysis = self._get_trend_analysis(base_query)
            
            # Alerts and notifications
            alerts = self._get_system_alerts()
            
            dashboard_data = {
                "summary": summary_stats,
                "approval_workflow": approval_stats,
                "geographic_breakdown": geographic_breakdown,
                "user_activity": user_activity_stats,
                "system_metrics": system_metrics,
                "trend_analysis": trend_analysis,
                "alerts": alerts,
                "generated_at": datetime.utcnow().isoformat()
            }
            
            # Cache the results
            self._set_cache(cache_key, dashboard_data)
            
            return ServiceResult.success_result(data=dashboard_data)
            
        except Exception as e:
            return ServiceResult.error_result(f"Error generating BO dashboard: {str(e)}")
    
    def get_comparative_analysis(self, comparison_type: str = "year_over_year",
                                base_filters: Dict[str, Any] = None) -> ServiceResult:
        """
        Generate comparative analysis reports
        """
        try:
            if comparison_type == "year_over_year":
                return self._get_year_over_year_analysis(base_filters)
            elif comparison_type == "season_comparison":
                return self._get_season_comparison_analysis(base_filters)
            elif comparison_type == "village_comparison":
                return self._get_village_comparison_analysis(base_filters)
            else:
                return ServiceResult.error_result(f"Unknown comparison type: {comparison_type}")
                
        except Exception as e:
            return ServiceResult.error_result(f"Error generating comparative analysis: {str(e)}")
    
    def _get_vo_summary_stats(self, base_query) -> Dict[str, Any]:
        """Get summary statistics for VO dashboard"""
        total_targets = base_query.count()
        total_area = base_query.with_entities(
            func.coalesce(func.sum(CropTarget.target_area), 0)
        ).scalar()
        
        approved_count = base_query.filter(
            CropTarget.status == CropTargetStatus.APPROVED.value
        ).count()
        
        pending_count = base_query.filter(
            CropTarget.status == CropTargetStatus.SUBMITTED.value
        ).count()
        
        rejected_count = base_query.filter(
            CropTarget.status == CropTargetStatus.REJECTED.value
        ).count()
        
        # Calculate approval rate
        approval_rate = (approved_count / total_targets * 100) if total_targets > 0 else 0
        
        return {
            "total_targets": total_targets,
            "total_area": float(total_area or 0),
            "approved_targets": approved_count,
            "pending_targets": pending_count,
            "rejected_targets": rejected_count,
            "approval_rate": round(approval_rate, 2),
            "total_cultivable_area": 1000.0,  # Mock data - should come from village master
            "area_utilization_rate": round(float(total_area or 0) / 1000.0 * 100, 2)
        }
    
    def _get_bo_summary_stats(self, base_query) -> Dict[str, Any]:
        """Get summary statistics for BO dashboard"""
        total_submissions = base_query.count()
        
        # Aggregate statistics by status
        status_stats = base_query.with_entities(
            CropTarget.status,
            func.count(CropTarget.id).label('count'),
            func.coalesce(func.sum(CropTarget.target_area), 0).label('total_area')
        ).group_by(CropTarget.status).all()
        
        status_summary = {}
        total_area = 0
        
        for status, count, area in status_stats:
            status_summary[status] = {
                "count": count,
                "total_area": float(area or 0)
            }
            total_area += float(area or 0)
        
        # Pending approvals requiring attention
        pending_count = status_summary.get(CropTargetStatus.SUBMITTED.value, {}).get('count', 0)
        
        # Active users count
        active_users = self.db.query(User).filter(
            User.is_active == True,
            User.deleted_at.is_(None)
        ).count()
        
        return {
            "total_submissions": total_submissions,
            "total_area": total_area,
            "pending_approvals": pending_count,
            "active_users": active_users,
            "status_breakdown": status_summary
        }
    
    def _get_status_breakdown(self, base_query) -> Dict[str, Dict[str, Any]]:
        """Get detailed status breakdown"""
        status_stats = base_query.with_entities(
            CropTarget.status,
            func.count(CropTarget.id).label('count'),
            func.coalesce(func.sum(CropTarget.target_area), 0).label('total_area'),
            func.avg(CropTarget.target_area).label('avg_area')
        ).group_by(CropTarget.status).all()
        
        return {
            status: {
                "count": count,
                "total_area": float(total_area or 0),
                "average_area": float(avg_area or 0)
            }
            for status, count, total_area, avg_area in status_stats
        }
    
    def _get_crop_breakdown(self, base_query) -> List[Dict[str, Any]]:
        """Get crop type breakdown"""
        crop_stats = base_query.with_entities(
            CropTarget.crop,
            func.count(CropTarget.id).label('count'),
            func.coalesce(func.sum(CropTarget.target_area), 0).label('total_area')
        ).group_by(CropTarget.crop).order_by(
            func.count(CropTarget.id).desc()
        ).limit(10).all()
        
        return [
            {
                "crop": crop,
                "count": count,
                "total_area": float(total_area or 0),
                "percentage": round(count / base_query.count() * 100, 2) if base_query.count() > 0 else 0
            }
            for crop, count, total_area in crop_stats
        ]
    
    def _get_timeline_data(self, base_query) -> List[Dict[str, Any]]:
        """Get timeline data for trend analysis"""
        timeline_stats = base_query.with_entities(
            extract('month', CropTarget.planting_date).label('month'),
            extract('year', CropTarget.planting_date).label('year'),
            func.count(CropTarget.id).label('count'),
            func.coalesce(func.sum(CropTarget.target_area), 0).label('total_area')
        ).group_by('year', 'month').order_by('year', 'month').all()
        
        return [
            {
                "month": int(month),
                "year": int(year),
                "count": count,
                "total_area": float(total_area or 0),
                "date_key": f"{int(year)}-{int(month):02d}"
            }
            for month, year, count, total_area in timeline_stats
        ]
    
    def _get_recent_activities(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent activities for the user"""
        activities = self.db.query(AuditLog).filter(
            AuditLog.user_id == user_id,
            AuditLog.resource_type == "crop_target"
        ).order_by(AuditLog.timestamp.desc()).limit(limit).all()
        
        return [activity.get_summary() for activity in activities]
    
    def _get_vo_performance_metrics(self, base_query) -> Dict[str, Any]:
        """Calculate performance metrics for VO"""
        total_targets = base_query.count()
        
        if total_targets == 0:
            return {
                "submission_efficiency": 0,
                "approval_success_rate": 0,
                "average_processing_time": 0,
                "target_completion_rate": 0
            }
        
        # Calculate metrics
        approved_targets = base_query.filter(
            CropTarget.status == CropTargetStatus.APPROVED.value
        ).count()
        
        # Average time from submission to approval
        avg_processing_time = base_query.filter(
            CropTarget.submitted_at.isnot(None),
            CropTarget.approved_at.isnot(None)
        ).with_entities(
            func.avg(
                func.extract('epoch', CropTarget.approved_at - CropTarget.submitted_at) / 86400
            ).label('avg_days')
        ).scalar()
        
        return {
            "submission_efficiency": round((total_targets / 30) * 100, 2),  # Targets per month
            "approval_success_rate": round(approved_targets / total_targets * 100, 2),
            "average_processing_time": round(float(avg_processing_time or 0), 1),
            "target_completion_rate": round(approved_targets / total_targets * 100, 2)
        }
    
    def _get_approval_workflow_stats(self, base_query) -> Dict[str, Any]:
        """Get approval workflow statistics for BO"""
        # Workflow transition statistics
        workflow_stats = base_query.with_entities(
            CropTarget.status,
            func.count(CropTarget.id).label('count'),
            func.avg(
                case(
                    (and_(CropTarget.submitted_at.isnot(None), CropTarget.approved_at.isnot(None)),
                     func.extract('epoch', CropTarget.approved_at - CropTarget.submitted_at) / 86400),
                    else_=None
                )
            ).label('avg_processing_days')
        ).group_by(CropTarget.status).all()
        
        # Overdue submissions (pending > 7 days)
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        overdue_count = base_query.filter(
            CropTarget.status == CropTargetStatus.SUBMITTED.value,
            CropTarget.submitted_at < seven_days_ago
        ).count()
        
        return {
            "workflow_statistics": {
                status: {
                    "count": count,
                    "average_processing_days": round(float(avg_days or 0), 1)
                }
                for status, count, avg_days in workflow_stats
            },
            "overdue_submissions": overdue_count,
            "processing_efficiency": self._calculate_processing_efficiency(base_query)
        }
    
    def _get_geographic_breakdown(self, base_query) -> List[Dict[str, Any]]:
        """Get geographic distribution of targets"""
        village_stats = base_query.with_entities(
            CropTarget.village,
            CropTarget.district,
            func.count(CropTarget.id).label('count'),
            func.coalesce(func.sum(CropTarget.target_area), 0).label('total_area')
        ).group_by(CropTarget.village, CropTarget.district).order_by(
            func.count(CropTarget.id).desc()
        ).limit(20).all()
        
        return [
            {
                "village": village,
                "district": district,
                "target_count": count,
                "total_area": float(total_area or 0)
            }
            for village, district, count, total_area in village_stats
        ]
    
    def _get_user_activity_stats(self) -> Dict[str, Any]:
        """Get user activity statistics"""
        # Active users in last 30 days
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        active_users_count = self.db.query(User).filter(
            User.last_login_at >= thirty_days_ago,
            User.is_active == True
        ).count()
        
        # User role distribution
        role_distribution = self.db.query(
            User.role,
            func.count(User.id).label('count')
        ).filter(
            User.is_active == True,
            User.deleted_at.is_(None)
        ).group_by(User.role).all()
        
        return {
            "active_users_30_days": active_users_count,
            "role_distribution": {
                role.value: count for role, count in role_distribution
            }
        }
    
    def _get_system_performance_metrics(self) -> Dict[str, Any]:
        """Get system performance metrics"""
        # Database statistics
        total_crop_targets = self.db.query(CropTarget).count()
        total_users = self.db.query(User).filter(User.deleted_at.is_(None)).count()
        total_audit_logs = self.db.query(AuditLog).count()
        
        # Recent system activity
        recent_activity = self.db.query(AuditLog).filter(
            AuditLog.timestamp >= datetime.utcnow() - timedelta(hours=24)
        ).count()
        
        return {
            "total_crop_targets": total_crop_targets,
            "total_users": total_users,
            "total_audit_logs": total_audit_logs,
            "activity_last_24h": recent_activity,
            "system_uptime": "99.9%",  # Mock data - would come from monitoring system
            "database_size": "150 MB"   # Mock data - would come from database metrics
        }
    
    def _get_trend_analysis(self, base_query) -> Dict[str, Any]:
        """Get trend analysis data"""
        # Monthly submission trends
        current_year = datetime.now().year
        monthly_trends = base_query.filter(
            extract('year', CropTarget.created_at) == current_year
        ).with_entities(
            extract('month', CropTarget.created_at).label('month'),
            func.count(CropTarget.id).label('count')
        ).group_by('month').order_by('month').all()
        
        # Calculate growth rate
        this_month = datetime.now().month
        last_month = this_month - 1 if this_month > 1 else 12
        
        this_month_count = next((count for month, count in monthly_trends if month == this_month), 0)
        last_month_count = next((count for month, count in monthly_trends if month == last_month), 0)
        
        growth_rate = 0
        if last_month_count > 0:
            growth_rate = ((this_month_count - last_month_count) / last_month_count) * 100
        
        return {
            "monthly_trends": [
                {"month": int(month), "count": count}
                for month, count in monthly_trends
            ],
            "growth_rate": round(growth_rate, 2),
            "trend_direction": "up" if growth_rate > 0 else "down" if growth_rate < 0 else "stable"
        }
    
    def _get_system_alerts(self) -> List[Dict[str, Any]]:
        """Get system alerts and notifications"""
        alerts = []
        
        # Check for overdue approvals
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        overdue_count = self.db.query(CropTarget).filter(
            CropTarget.status == CropTargetStatus.SUBMITTED.value,
            CropTarget.submitted_at < seven_days_ago
        ).count()
        
        if overdue_count > 0:
            alerts.append({
                "type": "warning",
                "title": "Overdue Approvals",
                "message": f"{overdue_count} crop targets pending approval for over 7 days",
                "action_url": "/bo/pending-approvals",
                "priority": "high"
            })
        
        # Check for locked accounts
        locked_users = self.db.query(User).filter(
            User.locked_until.isnot(None),
            User.locked_until > datetime.utcnow()
        ).count()
        
        if locked_users > 0:
            alerts.append({
                "type": "info",
                "title": "Locked Accounts",
                "message": f"{locked_users} user accounts are currently locked",
                "action_url": "/admin/users",
                "priority": "medium"
            })
        
        return alerts
    
    def _calculate_processing_efficiency(self, base_query) -> float:
        """Calculate overall processing efficiency"""
        # Targets processed within SLA (7 days)
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        
        total_processed = base_query.filter(
            CropTarget.status.in_([CropTargetStatus.APPROVED.value, CropTargetStatus.REJECTED.value])
        ).count()
        
        if total_processed == 0:
            return 100.0
        
        within_sla = base_query.filter(
            CropTarget.status.in_([CropTargetStatus.APPROVED.value, CropTargetStatus.REJECTED.value]),
            CropTarget.approved_at - CropTarget.submitted_at <= timedelta(days=7)
        ).count()
        
        return round((within_sla / total_processed) * 100, 2)
    
    def _get_year_over_year_analysis(self, base_filters: Dict[str, Any] = None) -> ServiceResult:
        """Generate year-over-year comparative analysis"""
        # Implementation would compare current year vs previous year metrics
        return ServiceResult.success_result(
            data={"analysis_type": "year_over_year", "status": "not_implemented"}
        )
    
    def _get_season_comparison_analysis(self, base_filters: Dict[str, Any] = None) -> ServiceResult:
        """Generate season-wise comparative analysis"""
        # Implementation would compare different seasons
        return ServiceResult.success_result(
            data={"analysis_type": "season_comparison", "status": "not_implemented"}
        )
    
    def _get_village_comparison_analysis(self, base_filters: Dict[str, Any] = None) -> ServiceResult:
        """Generate village-wise comparative analysis"""
        # Implementation would compare different villages
        return ServiceResult.success_result(
            data={"analysis_type": "village_comparison", "status": "not_implemented"}
        )
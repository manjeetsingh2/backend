"""
Audit service for comprehensive system logging and monitoring
Implements audit trail, compliance reporting, and activity tracking
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from .base import BaseService, ServiceResult
from models.audit import AuditLog, AuditAction
from models.user import User


class AuditService(BaseService[AuditLog]):
    """Comprehensive audit logging and monitoring service"""
    
    def __init__(self, db_session: Session):
        super().__init__(AuditLog, db_session)
    
    def log_user_action(self, user_id: str, username: str, action: AuditAction,
                       resource_type: str, resource_id: str = None,
                       description: str = None, old_values: Dict = None,
                       new_values: Dict = None, request_context: Dict = None) -> ServiceResult:
        """
        Log user action with comprehensive context
        """
        try:
            audit_log = AuditLog.log_user_action(
                user_id=user_id,
                username=username,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                description=description,
                old_values=old_values,
                new_values=new_values,
                **(request_context or {})
            )
            
            self.db.add(audit_log)
            self.db.commit()
            
            return ServiceResult.success_result(
                data=audit_log.get_summary(),
                message="Audit log created successfully"
            )
            
        except Exception as e:
            return ServiceResult.error_result(f"Error creating audit log: {str(e)}")
    
    def get_user_activity_log(self, user_id: str = None, username: str = None,
                             filters: Dict[str, Any] = None,
                             page: int = 1, per_page: int = 50) -> ServiceResult:
        """
        Get activity log for a specific user or all users
        """
        try:
            query = self.db.query(AuditLog)
            
            # Filter by user
            if user_id:
                query = query.filter(AuditLog.user_id == user_id)
            elif username:
                query = query.filter(AuditLog.username == username)
            
            # Apply additional filters
            if filters:
                if filters.get('action'):
                    query = query.filter(AuditLog.action == AuditAction(filters['action']))
                
                if filters.get('resource_type'):
                    query = query.filter(AuditLog.resource_type == filters['resource_type'])
                
                if filters.get('date_from'):
                    date_from = datetime.fromisoformat(filters['date_from'])
                    query = query.filter(AuditLog.timestamp >= date_from)
                
                if filters.get('date_to'):
                    date_to = datetime.fromisoformat(filters['date_to'])
                    query = query.filter(AuditLog.timestamp <= date_to)
                
                if filters.get('ip_address'):
                    query = query.filter(AuditLog.ip_address == filters['ip_address'])
            
            # Get total count
            total = query.count()
            
            # Apply pagination and ordering
            logs = query.order_by(AuditLog.timestamp.desc()).offset(
                (page - 1) * per_page
            ).limit(per_page).all()
            
            return ServiceResult.success_result(
                data={
                    "items": [log.get_summary() for log in logs],
                    "total": total,
                    "page": page,
                    "per_page": per_page,
                    "pages": (total + per_page - 1) // per_page
                }
            )
            
        except Exception as e:
            return ServiceResult.error_result(f"Error fetching activity log: {str(e)}")
    
    def get_system_activity_summary(self, time_period: str = "24h") -> ServiceResult:
        """
        Get system-wide activity summary for different time periods
        """
        try:
            # Calculate time range
            time_ranges = {
                "1h": timedelta(hours=1),
                "24h": timedelta(hours=24),
                "7d": timedelta(days=7),
                "30d": timedelta(days=30)
            }
            
            if time_period not in time_ranges:
                return ServiceResult.error_result(f"Invalid time period: {time_period}")
            
            start_time = datetime.utcnow() - time_ranges[time_period]
            
            # Activity by action type
            action_stats = self.db.query(
                AuditLog.action,
                func.count(AuditLog.id).label('count')
            ).filter(
                AuditLog.timestamp >= start_time
            ).group_by(AuditLog.action).all()
            
            # Activity by resource type
            resource_stats = self.db.query(
                AuditLog.resource_type,
                func.count(AuditLog.id).label('count')
            ).filter(
                AuditLog.timestamp >= start_time
            ).group_by(AuditLog.resource_type).all()
            
            # Top active users
            user_stats = self.db.query(
                AuditLog.username,
                func.count(AuditLog.id).label('activity_count')
            ).filter(
                AuditLog.timestamp >= start_time,
                AuditLog.username.isnot(None)
            ).group_by(AuditLog.username).order_by(
                func.count(AuditLog.id).desc()
            ).limit(10).all()
            
            # Hourly activity distribution
            hourly_stats = self.db.query(
                func.extract('hour', AuditLog.timestamp).label('hour'),
                func.count(AuditLog.id).label('count')
            ).filter(
                AuditLog.timestamp >= start_time
            ).group_by('hour').order_by('hour').all()
            
            # Security events (failed logins, account locks, etc.)
            security_events = self.db.query(AuditLog).filter(
                AuditLog.timestamp >= start_time,
                or_(
                    and_(AuditLog.action == AuditAction.LOGIN, 
                         AuditLog.business_context['login_success'].astext == 'false'),
                    AuditLog.business_context['action'].astext.in_(['account_lock', 'account_unlock'])
                )
            ).count()
            
            return ServiceResult.success_result(
                data={
                    "time_period": time_period,
                    "start_time": start_time.isoformat(),
                    "end_time": datetime.utcnow().isoformat(),
                    "total_activities": sum(count for _, count in action_stats),
                    "action_breakdown": {
                        action.value: count for action, count in action_stats
                    },
                    "resource_breakdown": {
                        resource: count for resource, count in resource_stats
                    },
                    "top_users": [
                        {"username": username, "activity_count": count}
                        for username, count in user_stats
                    ],
                    "hourly_distribution": [
                        {"hour": int(hour), "count": count}
                        for hour, count in hourly_stats
                    ],
                    "security_events": security_events
                }
            )
            
        except Exception as e:
            return ServiceResult.error_result(f"Error generating activity summary: {str(e)}")
    
    def get_security_events(self, filters: Dict[str, Any] = None,
                           page: int = 1, per_page: int = 25) -> ServiceResult:
        """
        Get security-related events for monitoring
        """
        try:
            # Base query for security events
            query = self.db.query(AuditLog).filter(
                or_(
                    AuditLog.action == AuditAction.LOGIN,
                    AuditLog.action == AuditAction.LOGOUT,
                    AuditLog.business_context['action'].astext.in_([
                        'account_lock', 'account_unlock', 'password_change'
                    ])
                )
            )
            
            # Apply filters
            if filters:
                if filters.get('event_type'):
                    if filters['event_type'] == 'failed_logins':
                        query = query.filter(
                            AuditLog.action == AuditAction.LOGIN,
                            AuditLog.business_context['login_success'].astext == 'false'
                        )
                    elif filters['event_type'] == 'successful_logins':
                        query = query.filter(
                            AuditLog.action == AuditAction.LOGIN,
                            AuditLog.business_context['login_success'].astext.is_(None)
                        )
                
                if filters.get('username'):
                    query = query.filter(AuditLog.username.ilike(f"%{filters['username']}%"))
                
                if filters.get('ip_address'):
                    query = query.filter(AuditLog.ip_address == filters['ip_address'])
                
                if filters.get('date_from'):
                    date_from = datetime.fromisoformat(filters['date_from'])
                    query = query.filter(AuditLog.timestamp >= date_from)
                
                if filters.get('date_to'):
                    date_to = datetime.fromisoformat(filters['date_to'])
                    query = query.filter(AuditLog.timestamp <= date_to)
            
            # Get total count
            total = query.count()
            
            # Apply pagination
            events = query.order_by(AuditLog.timestamp.desc()).offset(
                (page - 1) * per_page
            ).limit(per_page).all()
            
            # Enhance event data with security context
            enhanced_events = []
            for event in events:
                event_data = event.get_summary()
                
                # Add security-specific information
                if event.action == AuditAction.LOGIN:
                    login_success = event.business_context.get('login_success', True)
                    event_data['security_info'] = {
                        'event_type': 'failed_login' if login_success == False else 'successful_login',
                        'risk_level': 'high' if login_success == False else 'low'
                    }
                
                enhanced_events.append(event_data)
            
            return ServiceResult.success_result(
                data={
                    "items": enhanced_events,
                    "total": total,
                    "page": page,
                    "per_page": per_page,
                    "pages": (total + per_page - 1) // per_page
                }
            )
            
        except Exception as e:
            return ServiceResult.error_result(f"Error fetching security events: {str(e)}")
    
    def get_compliance_report(self, report_type: str = "monthly",
                             date_range: Dict[str, str] = None) -> ServiceResult:
        """
        Generate compliance reports for audit purposes
        """
        try:
            if not date_range:
                # Default to current month
                now = datetime.utcnow()
                start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                end_date = now
            else:
                start_date = datetime.fromisoformat(date_range['start'])
                end_date = datetime.fromisoformat(date_range['end'])
            
            # User activity summary
            user_activity = self.db.query(
                AuditLog.username,
                func.count(AuditLog.id).label('total_actions'),
                func.count(func.distinct(func.date(AuditLog.timestamp))).label('active_days'),
                func.min(AuditLog.timestamp).label('first_activity'),
                func.max(AuditLog.timestamp).label('last_activity')
            ).filter(
                AuditLog.timestamp.between(start_date, end_date),
                AuditLog.username.isnot(None)
            ).group_by(AuditLog.username).all()
            
            # Data modification tracking
            data_modifications = self.db.query(AuditLog).filter(
                AuditLog.timestamp.between(start_date, end_date),
                AuditLog.action.in_([AuditAction.CREATE, AuditAction.UPDATE, AuditAction.DELETE]),
                or_(AuditLog.old_values.isnot(None), AuditLog.new_values.isnot(None))
            ).count()
            
            # Administrative actions
            admin_actions = self.db.query(AuditLog).filter(
                AuditLog.timestamp.between(start_date, end_date),
                AuditLog.business_context['action'].astext.in_([
                    'account_lock', 'account_unlock', 'user_creation', 'user_deletion'
                ])
            ).count()
            
            # Access patterns analysis
            unique_ips = self.db.query(
                func.count(func.distinct(AuditLog.ip_address))
            ).filter(
                AuditLog.timestamp.between(start_date, end_date),
                AuditLog.ip_address.isnot(None)
            ).scalar()
            
            return ServiceResult.success_result(
                data={
                    "report_type": report_type,
                    "period": {
                        "start": start_date.isoformat(),
                        "end": end_date.isoformat(),
                        "duration_days": (end_date - start_date).days
                    },
                    "user_activity": [
                        {
                            "username": username,
                            "total_actions": total_actions,
                            "active_days": active_days,
                            "first_activity": first_activity.isoformat() if first_activity else None,
                            "last_activity": last_activity.isoformat() if last_activity else None
                        }
                        for username, total_actions, active_days, first_activity, last_activity in user_activity
                    ],
                    "system_metrics": {
                        "data_modifications": data_modifications,
                        "administrative_actions": admin_actions,
                        "unique_ip_addresses": unique_ips,
                        "total_audit_entries": len(user_activity)
                    },
                    "generated_at": datetime.utcnow().isoformat(),
                    "generated_by": "system"
                }
            )
            
        except Exception as e:
            return ServiceResult.error_result(f"Error generating compliance report: {str(e)}")
    
    def search_audit_logs(self, search_term: str, search_type: str = "description",
                         limit: int = 50) -> ServiceResult:
        """
        Search audit logs by various criteria
        """
        try:
            query = self.db.query(AuditLog)
            
            if search_type == "description":
                query = query.filter(AuditLog.description.ilike(f"%{search_term}%"))
            elif search_type == "username":
                query = query.filter(AuditLog.username.ilike(f"%{search_term}%"))
            elif search_type == "resource_id":
                query = query.filter(AuditLog.resource_id == search_term)
            elif search_type == "ip_address":
                query = query.filter(AuditLog.ip_address == search_term)
            else:
                # Search across multiple fields
                query = query.filter(
                    or_(
                        AuditLog.description.ilike(f"%{search_term}%"),
                        AuditLog.username.ilike(f"%{search_term}%"),
                        AuditLog.resource_type.ilike(f"%{search_term}%")
                    )
                )
            
            logs = query.order_by(AuditLog.timestamp.desc()).limit(limit).all()
            
            return ServiceResult.success_result(
                data=[log.get_summary() for log in logs],
                metadata={"search_term": search_term, "search_type": search_type, "results_count": len(logs)}
            )
            
        except Exception as e:
            return ServiceResult.error_result(f"Error searching audit logs: {str(e)}")
    
    def cleanup_old_logs(self, retention_days: int = 365) -> ServiceResult:
        """
        Clean up old audit logs beyond retention period
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
            
            # Count logs to be deleted
            logs_to_delete = self.db.query(AuditLog).filter(
                AuditLog.timestamp < cutoff_date
            ).count()
            
            if logs_to_delete == 0:
                return ServiceResult.success_result(
                    message="No logs to clean up",
                    metadata={"retention_days": retention_days}
                )
            
            # Delete old logs
            deleted_count = self.db.query(AuditLog).filter(
                AuditLog.timestamp < cutoff_date
            ).delete()
            
            self.db.commit()
            
            # Log the cleanup action
            cleanup_log = AuditLog.create_log(
                action=AuditAction.DELETE,
                resource_type="audit_log",
                description=f"Cleaned up {deleted_count} audit logs older than {retention_days} days",
                business_context={
                    "cleanup_action": "automatic_retention",
                    "retention_days": retention_days,
                    "deleted_count": deleted_count
                }
            )
            self.db.add(cleanup_log)
            self.db.commit()
            
            return ServiceResult.success_result(
                message=f"Successfully cleaned up {deleted_count} old audit logs",
                metadata={
                    "deleted_count": deleted_count,
                    "retention_days": retention_days,
                    "cutoff_date": cutoff_date.isoformat()
                }
            )
            
        except Exception as e:
            return ServiceResult.error_result(f"Error cleaning up audit logs: {str(e)}")
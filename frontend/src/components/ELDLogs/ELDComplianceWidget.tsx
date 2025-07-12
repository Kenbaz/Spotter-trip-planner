// import { Card, CardContent, CardHeader, CardTitle } from "../UI/Card";
// import { Button } from "../UI/Button";
// import { LoadingSpinner } from "../UI/LoadingSpinner";
// import {
//   FileText,
//   CheckCircle,
//   AlertTriangle,
//   Calendar,
//   ArrowRight,
//   RefreshCw,
// } from "lucide-react";
// import { ELDComplianceIndicator } from "./ELDComplianceIndicator";
// import { useComplianceSummary, useMyELDLogs } from "../../hooks/useELDLogs";
// import { Link } from "react-router-dom";

// interface ELDComplianceWidgetProps {
//   driverId: string;
//   showRecentLogs?: boolean;
//   showComplianceScore?: boolean;
//   dateRange?: {
//     start?: string;
//     end?: string;
//   };
//   className?: string;
// }

// export function ELDComplianceWidget({
// //   driverId,
//   showRecentLogs = true,
//   showComplianceScore = true,
//   dateRange,
//   className = "",
// }: ELDComplianceWidgetProps) {
//   // Get compliance summary for the specified date range (default last 30 days)
//   const {
//     data: complianceSummary,
//     isLoading: isSummaryLoading,
//     isError: isSummaryError,
//     refetch: refetchSummary,
//   } = useComplianceSummary(dateRange);

//   // Get recent logs if requested
//   const { data: recentLogsData, isLoading: isLogsLoading } = useMyELDLogs({
//     page_size: 5,
//     // Only fetch if we want to show recent logs
//     ...(showRecentLogs ? {} : { page_size: 0 }),
//   });

//   const handleRefresh = () => {
//     refetchSummary();
//   };

//   if (isSummaryLoading) {
//     return (
//       <Card className={className}>
//         <CardContent className="p-6">
//           <div className="flex items-center justify-center py-8">
//             <LoadingSpinner size="medium" text="Loading compliance data..." />
//           </div>
//         </CardContent>
//       </Card>
//     );
//   }

//   if (isSummaryError || !complianceSummary) {
//     return (
//       <Card className={`border-red-200 bg-red-50 ${className}`}>
//         <CardContent className="p-6">
//           <div className="flex items-center space-x-3">
//             <AlertTriangle className="w-6 h-6 text-red-600" />
//             <div>
//               <h3 className="font-medium text-red-800">
//                 Failed to Load Compliance Data
//               </h3>
//               <p className="text-sm text-red-700 mt-1">
//                 Unable to retrieve your ELD compliance information
//               </p>
//             </div>
//           </div>
//         </CardContent>
//       </Card>
//     );
//   }

//   const stats = complianceSummary.statistics;
//   const recentLogs = showRecentLogs ? recentLogsData?.results || [] : [];

//   return (
//     <Card className={className}>
//       <CardHeader>
//         <div className="flex justify-between items-center">
//           <CardTitle className="flex items-center text-lg">
//             <FileText className="w-5 h-5 mr-2" />
//             ELD Compliance
//           </CardTitle>

//           <div className="flex items-center space-x-2">
//             <Button
//               variant="ghost"
//               size="sm"
//               onClick={handleRefresh}
//               className="text-gray-500 hover:text-gray-700"
//             >
//               <RefreshCw className="w-4 h-4" />
//             </Button>

//             <Link to="/eld-logs">
//               <Button variant="ghost" size="sm">
//                 View All
//                 <ArrowRight className="w-4 h-4 ml-1" />
//               </Button>
//             </Link>
//           </div>
//         </div>
//       </CardHeader>

//       <CardContent className="space-y-6">
//         {/* Date Range */}
//         <div className="flex items-center text-sm text-gray-600">
//           <Calendar className="w-4 h-4 mr-2" />
//           <span>
//             {new Date(complianceSummary.date_range.start).toLocaleDateString()}{" "}
//             - {new Date(complianceSummary.date_range.end).toLocaleDateString()}
//           </span>
//         </div>

//         {/* Compliance Score */}
//         {showComplianceScore && (
//           <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
//             <div>
//               <div className="text-sm text-gray-600 mb-1">
//                 Overall Compliance
//               </div>
//               <ELDComplianceIndicator
//                 isCompliant={stats.compliance_rate >= 95}
//                 complianceScore={stats.average_compliance_score}
//                 violationCount={stats.total_violations}
//                 size="md"
//               />
//             </div>

//             <div className="text-right">
//               <div className="text-2xl font-bold text-gray-900">
//                 {stats.average_compliance_score.toFixed(1)}%
//               </div>
//               <div className="text-sm text-gray-600">Average Score</div>
//             </div>
//           </div>
//         )}

//         {/* Quick Stats Grid */}
//         <div className="grid grid-cols-2 gap-4">
//           <div className="text-center p-3 bg-green-50 rounded-lg">
//             <div className="text-xl font-bold text-green-600">
//               {stats.compliant_logs}
//             </div>
//             <div className="text-sm text-gray-600">Compliant Days</div>
//             <div className="text-xs text-green-600 mt-1">
//               {stats.compliance_rate.toFixed(1)}% rate
//             </div>
//           </div>

//           <div className="text-center p-3 bg-blue-50 rounded-lg">
//             <div className="text-xl font-bold text-blue-600">
//               {stats.certified_logs}
//             </div>
//             <div className="text-sm text-gray-600">Certified Logs</div>
//             <div className="text-xs text-blue-600 mt-1">
//               {stats.certification_rate.toFixed(1)}% rate
//             </div>
//           </div>
//         </div>

//         {/* Violations Summary */}
//         {stats.total_violations > 0 && (
//           <div className="p-3 bg-red-50 rounded-lg border border-red-200">
//             <div className="flex items-center justify-between">
//               <div className="flex items-center space-x-2">
//                 <AlertTriangle className="w-4 h-4 text-red-600" />
//                 <span className="font-medium text-red-800">
//                   {stats.total_violations} Active Violations
//                 </span>
//               </div>

//               <Link to="/eld-logs?compliance=non_compliant">
//                 <Button
//                   size="sm"
//                   variant="ghost"
//                   className="text-red-600 hover:text-red-700"
//                 >
//                   Review
//                 </Button>
//               </Link>
//             </div>

//             {/* Top violation types */}
//             {Object.entries(complianceSummary.violation_breakdown).length >
//               0 && (
//               <div className="mt-2 space-y-1">
//                 {Object.entries(complianceSummary.violation_breakdown)
//                   .sort(([, a], [, b]) => b - a)
//                   .slice(0, 2)
//                   .map(([type, count]) => (
//                     <div key={type} className="text-xs text-red-700">
//                       • {type.replace(/_/g, " ")}: {count}
//                     </div>
//                   ))}
//               </div>
//             )}
//           </div>
//         )}

//         {/* Recent Logs */}
//         {showRecentLogs && (
//           <div>
//             <div className="flex items-center justify-between mb-3">
//               <h4 className="font-medium text-gray-900">Recent Logs</h4>
//               {isLogsLoading && <LoadingSpinner size="sm" />}
//             </div>

//             {recentLogs.length === 0 ? (
//               <div className="text-center py-4 text-gray-500">
//                 <FileText className="w-8 h-8 mx-auto mb-2 text-gray-400" />
//                 <p className="text-sm">No recent logs found</p>
//               </div>
//             ) : (
//               <div className="space-y-2">
//                 {recentLogs.slice(0, 3).map((log) => (
//                   <div
//                     key={log.log_id}
//                     className="flex items-center justify-between p-2 bg-gray-50 rounded hover:bg-gray-100 transition-colors"
//                   >
//                     <div className="flex items-center space-x-3">
//                       <div className="text-sm">
//                         <div className="font-medium">
//                           {new Date(log.log_date).toLocaleDateString()}
//                         </div>
//                         <div className="text-gray-600 text-xs">
//                           {log.total_driving_hours.toFixed(1)}h driving
//                         </div>
//                       </div>
//                     </div>

//                     <div className="flex items-center space-x-2">
//                       {log.is_compliant ? (
//                         <CheckCircle className="w-4 h-4 text-green-600" />
//                       ) : (
//                         <AlertTriangle className="w-4 h-4 text-red-600" />
//                       )}

//                       {log.is_certified && (
//                         <FileText className="w-4 h-4 text-blue-600" />
//                       )}
//                     </div>
//                   </div>
//                 ))}

//                 {recentLogs.length > 3 && (
//                   <div className="text-center mt-2">
//                     <Link to="/eld-logs">
//                       <Button
//                         variant="ghost"
//                         size="sm"
//                         className="text-blue-600"
//                       >
//                         View {recentLogs.length - 3} more logs
//                       </Button>
//                     </Link>
//                   </div>
//                 )}
//               </div>
//             )}
//           </div>
//         )}

//         {/* Quick Actions */}
//         <div className="pt-3 border-t border-gray-200">
//           <div className="flex justify-between items-center">
//             <div className="text-xs text-gray-500">
//               Last updated: {new Date().toLocaleTimeString()}
//             </div>

//             <div className="flex space-x-2">
//               <Link to="/eld-logs?certified=uncertified">
//                 <Button size="sm" variant="ghost" className="text-blue-600">
//                   Certify Logs
//                 </Button>
//               </Link>

//               <Link to="/eld-logs">
//                 <Button size="sm" variant="secondary">
//                   Manage ELD
//                 </Button>
//               </Link>
//             </div>
//           </div>
//         </div>
//       </CardContent>
//     </Card>
//   );
// }

// // Simplified version for dashboard overview
// export function ELDComplianceOverview({
//   className = "",
// }: {
//   className?: string;
// }) {
//   const { data: complianceSummary, isLoading } = useComplianceSummary();

//   if (isLoading) {
//     return (
//       <div className={`p-4 bg-white rounded-lg border ${className}`}>
//         <div className="flex items-center justify-center py-4">
//           <LoadingSpinner size="sm" />
//         </div>
//       </div>
//     );
//   }

//   if (!complianceSummary) {
//     return (
//       <div
//         className={`p-4 bg-red-50 border border-red-200 rounded-lg ${className}`}
//       >
//         <div className="flex items-center space-x-2">
//           <AlertTriangle className="w-4 h-4 text-red-600" />
//           <span className="text-sm text-red-700">
//             Unable to load compliance data
//           </span>
//         </div>
//       </div>
//     );
//   }

//   const stats = complianceSummary.statistics;

//   return (
//     <div className={`p-4 bg-white rounded-lg border ${className}`}>
//       <div className="flex items-center justify-between mb-3">
//         <h3 className="font-medium text-gray-900 flex items-center">
//           <FileText className="w-4 h-4 mr-2" />
//           ELD Compliance
//         </h3>

//         <Link to="/eld-logs">
//           <Button variant="ghost" size="sm">
//             <ArrowRight className="w-4 h-4" />
//           </Button>
//         </Link>
//       </div>

//       <div className="space-y-3">
//         <div className="flex items-center justify-between">
//           <span className="text-sm text-gray-600">Compliance Rate</span>
//           <span className="font-semibold text-green-600">
//             {stats.compliance_rate.toFixed(1)}%
//           </span>
//         </div>

//         <div className="flex items-center justify-between">
//           <span className="text-sm text-gray-600">Certified Logs</span>
//           <span className="font-semibold text-blue-600">
//             {stats.certified_logs}/{stats.total_logs}
//           </span>
//         </div>

//         {stats.total_violations > 0 && (
//           <div className="flex items-center justify-between">
//             <span className="text-sm text-gray-600">Active Violations</span>
//             <span className="font-semibold text-red-600">
//               {stats.total_violations}
//             </span>
//           </div>
//         )}

//         <div className="pt-2 border-t border-gray-200">
//           <ELDComplianceIndicator
//             isCompliant={stats.compliance_rate >= 95}
//             complianceScore={stats.average_compliance_score}
//             violationCount={stats.total_violations}
//             size="sm"
//             showDetails={false}
//           />
//         </div>
//       </div>
//     </div>
//   );
// }

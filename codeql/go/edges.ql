/**
 * @name Call graph edges
 * @description One row per call site that may call another function in the graph.
 * @kind table
 * @id armwrestling/callgraph-edges
 */

import lib.CallGraph

from DataFlow::CallNode call, GraphFunction caller, GraphFunction callee
where callEdge(call, caller, callee)
select caller.getGraphId() as caller_id, callee.getGraphId() as callee_id,
  call.getLocation().getFile().getRelativePath() as call_file,
  call.getLocation().getStartLine() as call_line, callResolution(call, callee) as resolution

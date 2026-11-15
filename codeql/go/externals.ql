/**
 * @name Call graph external calls
 * @description One row per call from a graph function to a function declared outside the source.
 * @kind table
 * @id armwrestling/callgraph-externals
 */

import lib.CallGraph

from DataFlow::CallNode call, GraphFunction caller, Function target
where externalCall(call, caller, target)
select caller.getGraphId() as caller_id, target.getQualifiedName() as external_name,
  target.getPackage().getPath() as external_package,
  call.getLocation().getFile().getRelativePath() as call_file,
  call.getLocation().getStartLine() as call_line

/**
 * @name Call graph nodes
 * @description One row per function or method declared in the extracted source.
 * @kind table
 * @id armwrestling/callgraph-nodes
 */

import lib.CallGraph

from GraphFunction function
select function.getGraphId() as id, function.getName() as name,
  function.getPackagePath() as package, function.getRelativeFile() as file,
  function.getFirstLine() as start_line, function.getLastLine() as end_line

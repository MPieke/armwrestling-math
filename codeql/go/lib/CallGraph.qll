/**
 * Call graph definitions shared by `nodes.ql`, `edges.ql`, and any custom query
 * that needs ids and locations identical to the published graph.
 *
 * A node is a function or method declared in the extracted source. An edge is a
 * call site in one such function that may call another one. Calls to the
 * standard library or dependencies produce no edge, and a call inside a
 * function literal is attributed to the enclosing declared function.
 */

import go

/** Holds for repo-relative source files that belong in the graph (not Go tests). */
predicate isGraphFile(File file) {
  exists(file.getRelativePath()) and not file.getBaseName().regexpMatch(".*_test\\.go")
}

/** A function or method with a body, declared in a graph file. */
class GraphFunction extends FuncDecl {
  GraphFunction() { isGraphFile(this.getLocation().getFile()) and exists(this.getBody()) }

  /** A stable id: the Go package path and qualified name, e.g. `example.com/pkg.Type.Method`. */
  string getGraphId() { result = this.getFunction().getQualifiedName() }

  string getPackagePath() { result = this.getFunction().getPackage().getPath() }

  string getRelativeFile() { result = this.getLocation().getFile().getRelativePath() }

  int getFirstLine() { result = this.getLocation().getStartLine() }

  int getLastLine() { result = this.getBody().getLocation().getEndLine() }
}

/**
 * Holds if `call` is a call site inside `caller` that may call `callee`.
 * Dynamic dispatch is included as far as CodeQL resolves it.
 */
predicate callEdge(DataFlow::CallNode call, GraphFunction caller, GraphFunction callee) {
  call.asExpr().getParent*() = caller and
  callee = call.getACallee()
}

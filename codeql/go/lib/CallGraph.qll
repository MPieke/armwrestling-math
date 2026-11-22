/**
 * Call graph definitions shared by `nodes.ql`, `edges.ql`, `externals.ql`, and
 * any custom query that needs ids and locations identical to the published graph.
 *
 * A node is a function or method declared in the extracted source. An edge is a
 * call site in one such function that may call another one. Calls to the
 * standard library or dependencies are not edges; they are reported separately as
 * external calls. A call inside a function literal is attributed to the
 * enclosing declared function.
 */

import go

/** Holds for repo-relative source files that belong in the graph (not Go tests). */
predicate isGraphFile(File file) {
  exists(file.getRelativePath()) and not file.getBaseName().regexpMatch(".*_test\\.go")
}

/** Holds if `path` is the package path of a graph function declared directly in `directory`. */
private predicate packagePathOfDirectory(Container directory, string path) {
  exists(FuncDecl declaration, File file |
    file = declaration.getLocation().getFile() and
    isGraphFile(file) and
    file.getParentContainer() = directory and
    path = declaration.getFunction().getPackage().getPath()
  )
}

/** A function or method with a body, declared in a graph file. */
class GraphFunction extends FuncDecl {
  GraphFunction() { isGraphFile(this.getLocation().getFile()) and exists(this.getBody()) }

  /**
   * A stable id: the Go package path and qualified name, e.g.
   * `example.com/pkg.Type.Method`. A package may declare several `init`
   * functions, so those also carry their file and line.
   */
  string getGraphId() {
    if this.isInit()
    then
      result =
        this.getPackagePath() + ".init@" + this.getRelativeFile() + ":" +
          this.getFirstLine().toString()
    else result = this.getFunction().getQualifiedName()
  }

  /**
   * The Go package path. `init` functions have no package entity, so theirs is
   * taken from the other functions in the same directory (falling back to the
   * directory path if there are none).
   */
  string getPackagePath() {
    if exists(this.getFunction().getPackage())
    then result = this.getFunction().getPackage().getPath()
    else (
      packagePathOfDirectory(this.getLocation().getFile().getParentContainer(), result)
      or
      not packagePathOfDirectory(this.getLocation().getFile().getParentContainer(), _) and
      result = this.getLocation().getFile().getParentContainer().getRelativePath()
    )
  }

  string getRelativeFile() { result = this.getLocation().getFile().getRelativePath() }

  int getFirstLine() { result = this.getLocation().getStartLine() }

  int getLastLine() { result = this.getBody().getLocation().getEndLine() }

  /** Holds for the `main` function of a `main` package. */
  predicate isMain() {
    this.getName() = "main" and
    not this.getFunction() instanceof Method and
    this.getFunction().getPackage().getName() = "main"
  }

  /** Holds for a package-level `init` function. */
  predicate isInit() { this.getName() = "init" and not this.getFunction() instanceof Method }

  /**
   * Holds if a package-level initializer (code outside any function, such as
   * `var x = f()`) calls this function. Such calls run at program start and
   * create no edge, so the callee must not look unreferenced.
   */
  predicate isCalledAtPackageInit() {
    exists(DataFlow::CallNode call |
      call.getACallee() = this and
      isGraphFile(call.getLocation().getFile()) and
      not exists(FuncDef enclosing | call.asExpr().getParent*() = enclosing)
    )
  }

  /** Holds if the name is exported (starts with an upper-case letter). */
  predicate isExported() { this.getName().regexpMatch("\\p{Lu}.*") }

  /**
   * Holds if the function is used as a value (passed, stored, or assigned)
   * instead of being called directly, as handlers and callbacks are.
   */
  predicate isReferencedAsValue() {
    exists(Ident reference | reference = this.getFunction().getAReference() |
      not reference.getParent() instanceof FuncDecl and
      not exists(CallExpr call |
        call.getCalleeExpr() = reference or call.getCalleeExpr() = reference.getParent()
      )
    )
  }

  /** Holds if some other graph function calls this one (recursion does not count). */
  predicate hasCaller() {
    exists(DataFlow::CallNode call, GraphFunction caller |
      callEdge(call, caller, this) and caller != this
    )
  }

  /**
   * How the function is entered from outside the call graph, or the empty
   * string if it is only ever called by other graph functions. `unreferenced`
   * functions are dead-code candidates.
   */
  string getRootKind() {
    if this.isMain()
    then result = "main"
    else
      if this.isInit() or this.isCalledAtPackageInit()
      then result = "init"
      else
        if this.isReferencedAsValue()
        then result = "referenced"
        else
          if this.hasCaller()
          then result = ""
          else
            if this.isExported()
            then result = "exported-uncalled"
            else result = "unreferenced"
  }
}

/**
 * Holds if `call` is a call site inside `caller` that may call `callee`.
 * Dynamic dispatch is included as far as CodeQL resolves it.
 */
predicate callEdge(DataFlow::CallNode call, GraphFunction caller, GraphFunction callee) {
  call.asExpr().getParent*() = caller and
  callee = call.getACallee()
}

/** `static` if the call names the callee directly, `dynamic` if it was resolved via dispatch. */
string callResolution(DataFlow::CallNode call, GraphFunction callee) {
  if call.getTarget() = callee.getFunction() then result = "static" else result = "dynamic"
}

/**
 * Holds if `call` in `caller` calls `target`, a function declared outside the
 * extracted source (standard library or a dependency).
 */
predicate externalCall(DataFlow::CallNode call, GraphFunction caller, Function target) {
  call.asExpr().getParent*() = caller and
  target = call.getTarget() and
  exists(target.getPackage()) and
  not exists(target.(DeclaredEntity).getDeclaration().getFile().getRelativePath())
}

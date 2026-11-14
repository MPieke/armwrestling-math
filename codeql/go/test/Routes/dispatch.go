package main

type Saver interface {
	Save()
}

type diskSaver struct{}

func (diskSaver) Save() {}

type memSaver struct{}

func (memSaver) Save() {}

func useSaver(s Saver) { s.Save() }

func withClosure() {
	run := func() { leafClosure() }
	run()
}

func leafClosure() {}

var registry = map[string]func(){"x": viaMap}

func viaMap() {}

func runRegistry() { registry["x"]() }

var initialized = makeTable()

func makeTable() int { return 1 }

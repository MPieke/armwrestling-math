package main

import (
	"net/http"
	"os"
)

func main() {
	http.HandleFunc("/a", handleA)
	http.HandleFunc("/b", handleB)
	http.HandleFunc("/c", handleC)
	http.HandleFunc("/e", handleE)
	http.HandleFunc("/f", handleF)
	http.ListenAndServe(":0", nil)
}

func init() {}

func Exported() {}

func unusedHelper() { deadLeaf() }

func deadLeaf() {}

func handleA(w http.ResponseWriter, r *http.Request) { gateway() }

func handleB(w http.ResponseWriter, r *http.Request) { gateway() }

func gateway() { writeFile() }

func writeFile() { _ = os.WriteFile("a.txt", nil, 0o644) }

func handleC(w http.ResponseWriter, r *http.Request) { fetch() }

func fetch() {
	viaCache()
	viaDisk()
}

func viaCache() { load() }

func viaDisk() { load() }

func load() { _, _ = os.ReadFile("b.txt") }

func handleE(w http.ResponseWriter, r *http.Request) { serviceE() }

func handleF(w http.ResponseWriter, r *http.Request) { serviceF() }

func serviceE() { store() }

func serviceF() { store() }

func store() { _, _ = os.Open("c.txt") }

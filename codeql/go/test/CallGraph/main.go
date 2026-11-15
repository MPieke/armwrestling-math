package main

func main() {
	run()
	helper()
}

func run() {
	helper()
	leaf()
}

func helper() {
	leaf()
}

func leaf() {}

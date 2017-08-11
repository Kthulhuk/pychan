package main

import (
	"fmt"
	"reflect"
	"runtime"
	"time"
)

// The select should block,
// Then, the <- ch1 case should be executed very soon after the other goroutine
// times out.
// Expected output :
// -----------------
// Writing 42 to ch1
// Waited 1.00[0-9]*s
func read() {

	ch1 := make(chan int)

	go func() {
		time.Sleep(1 * time.Second)
		fmt.Println("Writing 42 to ch1")
		ch1 <- 42
	}()

	start := time.Now()
	select {
	case _ = <-ch1:
		elapsed := time.Since(start)
		fmt.Println("Waited", elapsed)
	}

}

// The select should execute the default code as many times as needed
// (hopefully once)
// Then the <-ch1 case should happen
// Expected output :
// -----------------
// Selected default behavior
// Writing 42 to ch1
// Received number 42 from ch1 after 1[0-9].[0-9]*µs
func read_default() {

	ch1 := make(chan int)
	ch2 := make(chan int)

	go func(ch2 chan int) {
		_ = <-ch2
		fmt.Println("Writing 42 to ch1")
		ch1 <- 42
	}(ch2)

	from_ch1 := 0
	wrote_to_ch2 := false
	start := time.Now()
	for from_ch1 == 0 {
		select {
		case from_ch1 = <-ch1:
			elapsed := time.Since(start)
			fmt.Println("Received number", from_ch1, "from ch1 after", elapsed)
		default:
			fmt.Println("Selected default behavior")
			if !wrote_to_ch2 {
				ch2 <- 1
				wrote_to_ch2 = true
			}
		}
	}
}

// Two channels can be read and there's a default clause
// Expected output :
// -----------------
// Writing (42|51) to ch(1|2)
// Writing (42|51) to ch(1|2)
// Received number (42|51) from ch(1|2)
func read_read_default() {

	ch1 := make(chan int)
	ch2 := make(chan int)

	go func() {
		fmt.Println("Writing 42 to ch1")
		ch1 <- 42
	}()

	go func() {
		fmt.Println("Writing 51 to ch2")
		ch2 <- 51
	}()

	time.Sleep(100 * time.Millisecond) // Hopefully this is enough time to let
	// the other two goroutines block on their channel writes

	var nb int
	select {
	case nb = <-ch1:
		fmt.Println("Received number", nb, "from ch1")
	case nb = <-ch2:
		fmt.Println("Received number", nb, "from ch2")
	default:
		panic("Selected default behavior")
	}

	if nb == 42 { // <-ch1 happened
		if <-ch2 != 51 {
			panic("We should be able to read '51' from ch2")
		}
	} else if nb == 51 { //<-ch2 happened
		if <-ch1 != 42 {
			panic("We should be able to read '42' from ch2")
		}
	} else {
		panic("WTF ?")
	}
}

// Two channels can be read and no default clause
// Expected output :
// -----------------
// Writing (42|51) to ch(1|2)
// Writing (42|51) to ch(1|2)
// Received number (42|51) from ch(1|2)
func read_read() {

	ch1 := make(chan int)
	ch2 := make(chan int)

	go func() {
		fmt.Println("Writing 42 to ch1")
		ch1 <- 42
	}()

	go func() {
		fmt.Println("Writing 51 to ch2")
		ch2 <- 51
	}()

	time.Sleep(100 * time.Millisecond) // Hopefully this is enough time to let
	// the other two goroutin block on their channel write or read

	var nb int
	select {
	case nb = <-ch1:
		fmt.Println("Received number", nb, "from ch1")
	case nb = <-ch2:
		fmt.Println("Received number", nb, "from ch2")
	}

	if nb == 42 { // <-ch1 happened
		if <-ch2 != 51 {
			panic("We should be able to read '51' from ch2")
		}
	} else if nb == 51 { //<-ch2 happened
		if <-ch1 != 42 {
			panic("We should be able to read '42' from ch2")
		}
	} else {
		panic("WTF ?")
	}
}

// One channel can be read, the written and there's a default clause
// Expected output :
// -----------------
// (Writing 42 to ch1|Reading from ch2)
// (Writing 42 to ch1|Reading from ch2)
// (Received number 42 from ch1|Sent number 51 to ch2)
func read_write_default() {

	ch1 := make(chan int)
	ch2 := make(chan int)

	go func() {
		fmt.Println("Writing 42 to ch1")
		ch1 <- 42
	}()

	go func() {
		fmt.Println("Reading from ch2")
		x := <-ch2
		ch1 <- x
	}()

	time.Sleep(100 * time.Millisecond) // Hopefully this is enough time to let
	// the other two goroutines block on their channel write or read

	nb := 51

	select {
	case nb = <-ch1:
		fmt.Println("Received number", nb, "from ch1")
	case ch2 <- nb:
		fmt.Println("Sent number", nb, "to ch2")
	default:
		panic("Selected default behavior")
	}

	if nb == 42 { // <-ch1 happened
		ch2 <- 17
		if <-ch1 != 17 {
			panic("We should be able to read 17 from ch1")
		}
	} else if nb == 51 { // ch2<- happened
		if <-ch1 != 42 {
			panic("We should be able to read '42' from ch2")
		}
	} else {
		panic("WTF ?")
	}
}

// One channel can be read, the other written and no default clause
// Expected output :
// -----------------
// (Writing 42 to ch1|Reading from ch2)
// (Writing 42 to ch1|Reading from ch2)
// (Received number 42 from ch1|Sent number 51 to ch2)
func read_write() {

	ch1 := make(chan int)
	ch2 := make(chan int)

	go func() {
		fmt.Println("Writing 42 to ch1")
		ch1 <- 42
	}()

	go func() {
		fmt.Println("Reading from ch2")
		x := <-ch2
		ch1 <- x
	}()

	time.Sleep(100 * time.Millisecond) // Hopefully this is enough time to let
	// the other two goroutines block on their channel write or read

	nb := 51

	select {
	case nb = <-ch1:
		fmt.Println("Received number", nb, "from ch1")
	case ch2 <- nb:
		fmt.Println("Sent number", nb, "to ch2")
	}

	if nb == 42 { // <-ch1 happened
		ch2 <- 17
		if <-ch1 != 17 {
			panic("We should be able to read 17 from ch1")
		}
	} else if nb == 51 { // ch2<- happened
		if <-ch1 != 42 {
			panic("We should be able to read '42' from ch2")
		}
	} else {
		panic("WTF ?")
	}
}

// Two channels can be written and there's a default clause
// Expected output :
// -----------------
// Reading from ch(1|2)
// Reading from ch(1|2)
// Sent number (42|51) to ch(1|2)
func write_write_default() {

	ch1A := make(chan int)
	ch1B := make(chan int)
	ch2A := make(chan int)
	ch2B := make(chan int)

	go func() {
		fmt.Println("Reading from ch1")
		x := <-ch1A
		ch1B <- x
	}()

	go func() {
		fmt.Println("Reading from ch2")
		x := <-ch2A
		ch2B <- x
	}()

	time.Sleep(100 * time.Millisecond) // Hopefully this is enough time to let
	// the other two goroutines block on their channel write or read

	nb1 := 42
	nb2 := 51
	sent := 0

	select {
	case ch1A <- nb1:
		fmt.Println("Sent number", nb1, "to ch1")
		sent = nb1
	case ch2A <- nb2:
		fmt.Println("Sent number", nb2, "to ch2")
		sent = nb2
	default:
		panic("Selected default behavior")
	}

	if sent == 42 { // ch1A <- happened
		ch2A <- 17 //Making sure ch2A<- did not already happen
		if <-ch1B != 42 {
			panic("We should be able to read 42 from ch1B")
		}
	} else if sent == 51 { // ch2A <- happened
		ch1A <- 17
		if <-ch2B != 51 {
			panic("We should be able to read 51 from ch2B")
		}
	} else {
		panic("WTF ?")
	}

}

// Two channels can be written and no default clause
// Expected output :
// -----------------
// Reading from ch(1|2)
// Reading from ch(1|2)
// Sent number (42|51) to ch(1|2)
func write_write() {
	ch1A := make(chan int)
	ch1B := make(chan int)
	ch2A := make(chan int)
	ch2B := make(chan int)

	go func() {
		fmt.Println("Reading from ch1")
		x := <-ch1A
		ch1B <- x
	}()

	go func() {
		fmt.Println("Reading from ch2")
		x := <-ch2A
		ch2B <- x
	}()

	time.Sleep(100 * time.Millisecond) // Hopefully this is enough time to let
	// the other two goroutines block on their channel write or read

	nb1 := 42
	nb2 := 51
	sent := 0

	select {
	case ch1A <- nb1:
		fmt.Println("Sent number", nb1, "to ch1")
		sent = nb1
	case ch2A <- nb2:
		fmt.Println("Sent number", nb2, "to ch2")
		sent = nb2
	}

	if sent == 42 { // ch1A <- happened
		ch2A <- 17 //Making sure ch2A<- did not already happen
		if <-ch1B != 42 {
			panic("We should be able to read 42 from ch1B")
		}
	} else if sent == 51 { // ch2A <- happened
		ch1A <- 17
		if <-ch2B != 51 {
			panic("We should be able to read 51 from ch2B")
		}
	} else {
		panic("WTF ?")
	}
}

// Main function that execute each test
func main() {
	tests := []func(){
		read,
		read_default,
		read_read,
		read_read_default,
		read_write,
		read_write_default,
		write_write,
		write_write_default}
	for _, f := range tests {
		fmt.Println(">>> Starting test", runtime.FuncForPC(reflect.ValueOf(f).Pointer()).Name(), "<<<")
		f()
		fmt.Println(">>> Test", runtime.FuncForPC(reflect.ValueOf(f).Pointer()).Name(), "over <<<")
		fmt.Println("")
	}
}

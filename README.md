<h1>CombinatorX</h1>

<p><strong>CombinatorX</strong> is a powerful, retro-styled Lambda Calculus and Combinatory Logic workbench running entirely in your terminal. It features a custom TUI (Text User Interface), real-time graph reduction, type inference, and a comprehensive standard library of combinators.</p>

<h2>Features</h2>

<ul>
    <li><strong>Interactive REPL</strong>: A command-line interface to define functions, evaluate expressions, and explore logic.</li>
    <li><strong>Graph Reduction Engine</strong>: Efficient evaluation of lambda terms using graph reduction, supporting recursion and deep computations.</li>
    <li><strong>Type Inference</strong>: Hindley-Milner type system to check expressions before execution (<code>type \x.x</code>).</li>
    <li><strong>Visual TUI</strong>: A windowed interface with support for themes, resizing, and scrolling.</li>
    <li><strong>Standard Library</strong>: Built-in definitions for Church Arithmetic, Boolean Logic, Lists, and standard Combinators (S, K, I, Y, etc.).</li>
    <li><strong>Dynamic Theming</strong>: Switch between various visual themes (e.g., Neon Night, Solarized, Dracula) on the fly.</li>
    <li><strong>Encyclopedia</strong>: Integral documentation system to look up definitions of combinators and theoretical concepts on the fly.</li>
    <li><strong>Intro Animation</strong>: A Matrix-inspired startup sequence.</li>
</ul>

<h2>Requirements</h2>

<ul>
    <li>Python 3.6+</li>
    <li>Standard Python libraries (no external <code>pip</code> dependencies required).</li>
    <li>A terminal with ANSI color support.</li>
</ul>

<h2>Installation</h2>

<p>Clone the repository or download the source code:</p>

<pre><code>git clone https://github.com/Sudo-Aju/CombinatorX.git
cd CombinatorX
</code></pre>

<h2>Usage</h2>

<p>Run the application directly with Python:</p>

<pre><code>python3 CombinatorX.py
</code></pre>

<h3>Commands</h3>

<p>Inside the REPL, you can use the following commands:</p>

<ul>
    <li><strong>Evaluation</strong>: Just type an expression to evaluate it.
        <pre><code>&gt; (\x. x) y
= y</code></pre>
    </li>
    <li><strong>Definitions</strong>: Bind a name to an expression.
        <pre><code>&gt; def ID = \x. x</code></pre>
    </li>
    <li><strong>Type Checking</strong>: Check the type of an expression.
        <pre><code>&gt; type \x. x
a -&gt; a</code></pre>
    </li>
    <li><strong>Reduction</strong>: Force full reduction of a term.
        <pre><code>&gt; reduce ADD ONE TWO</code></pre>
    </li>
    <li><strong>Documentation</strong>: Access the built-in encyclopedia.
        <pre><code>&gt; doc S
S: The Starling combinator. S x y z = x z (y z)...</code></pre>
    </li>
    <li><strong>Themes</strong>: Switch the visual theme.
        <pre><code>&gt; theme list
&gt; theme Solarized Light</code></pre>
    </li>
    <li><strong>Macros</strong>: View all defined combinators and standard library functions.
        <pre><code>&gt; macros
(or use 'lib')</code></pre>
    </li>
    <li><strong>Secrets</strong>: Unlock hidden features.
        <pre><code>&gt; matrix</code></pre>
    </li>
    <li><strong>Quit</strong>: Exit the application.
        <pre><code>&gt; quit</code></pre>
    </li>
</ul>

<h3>Key Bindings</h3>

<table border="1">
    <thead>
        <tr>
            <th>Key</th>
            <th>Action</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td><strong>F1</strong></td>
            <td>Toggle Help / Guide</td>
        </tr>
        <tr>
            <td><strong>F2</strong></td>
            <td>Save Configuration (Simulated)</td>
        </tr>
        <tr>
            <td><strong>F3</strong></td>
            <td>Load Configuration (Simulated)</td>
        </tr>
        <tr>
            <td><strong>Up / Down</strong></td>
            <td>Scroll Command History</td>
        </tr>
        <tr>
            <td><strong>PageUp / PageDown</strong></td>
            <td>Scroll Help Text</td>
        </tr>
        <tr>
            <td><strong>Left / Right</strong></td>
            <td>Navigate Help Chapters</td>
        </tr>
        <tr>
            <td><strong>Ctrl+C</strong></td>
            <td>Interrupt / Quit</td>
        </tr>
    </tbody>
</table>

<h2>Examples</h2>

<p><strong>Boolean Logic:</strong></p>
<pre><code>&gt; AND TRUE FALSE
= FALSE</code></pre>

<p><strong>Church Numerals:</strong></p>
<pre><code>&gt; ADD ONE TWO
= \f x. f (f (f x))  (which is 3)</code></pre>

<p><strong>Recursion (Factorial):</strong></p>
<pre><code>&gt; FAC (Succ (Succ (Succ Zero)))</code></pre>

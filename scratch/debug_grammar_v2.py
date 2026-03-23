from llama_cpp import LlamaGrammar
import logging

def test_grammar():
    agent_names = ["CustomerCare", "ShoppingTool", "Fallback"]
    choices_str = " | ".join(f'"{name}"' for name in agent_names)
    
    # Mirroring llama_cpp_router/main.py precisely
    grammar_rules = [
        r'root ::= "{" space target space "}"',
        r'target ::= "\"route\"" space ":" space route_choice',
        f'route_choice ::= {choices_str}',
        r'space ::= " "?'
    ]
    grammar_str = "\n".join(grammar_rules)
    print(f"Grammar string (len={len(grammar_str)}):\n{grammar_str}")
    
    try:
        grammar = LlamaGrammar.from_string(grammar_str)
        print("Success!")
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    test_grammar()

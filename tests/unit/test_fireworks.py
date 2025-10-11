"""Comprehensive Fireworks API test."""
import json
import requests
from backend.config import get_settings
from backend.providers.fireworks import FireworksJudge

def test_basic_connection():
    """Test 1: Basic API connection"""
    print("\n" + "="*70)
    print("TEST 1: BASIC API CONNECTION")
    print("="*70)
    
    settings = get_settings()
    
    print(f"API Key (first 10 chars): {settings.fireworks_api_key[:10]}...")
    print(f"Base URL: {settings.fireworks_base_url}")
    print(f"Model: {settings.fireworks_model}")
    
    headers = {
        "Authorization": f"Bearer {settings.fireworks_api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": settings.fireworks_model,
        "messages": [
            {"role": "user", "content": "Hello, test"}
        ],
        "max_tokens": 10
    }
    
    response = requests.post(
        f"{settings.fireworks_base_url}/chat/completions",
        headers=headers,
        json=data
    )
    
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response: {response.text[:500]}")
    
    if response.status_code == 200:
        print("✓ Basic connection successful")
        return True
    else:
        print("✗ Basic connection failed")
        return False


def test_json_instruction():
    """Test 2: JSON-only instruction following"""
    print("\n" + "="*70)
    print("TEST 2: JSON INSTRUCTION FOLLOWING")
    print("="*70)
    
    settings = get_settings()
    
    headers = {
        "Authorization": f"Bearer {settings.fireworks_api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": settings.fireworks_model,
        "messages": [
            {"role": "system", "content": "You are a JSON-only API. Respond ONLY with valid JSON."},
            {"role": "user", "content": 'Return this JSON: {"test": true, "value": 42}'}
        ],
        "temperature": 0.0,
        "max_tokens": 100
    }
    
    response = requests.post(
        f"{settings.fireworks_base_url}/chat/completions",
        headers=headers,
        json=data
    )
    
    print(f"\nStatus Code: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        message = result.get("choices", [{}])[0].get("message", {})
        
        # Check both content and reasoning_content
        content = message.get("content") or message.get("reasoning_content")
        
        print(f"\nRaw Response Content:")
        print("-" * 70)
        print(content)
        print("-" * 70)
        
        # Try to parse as JSON
        try:
            parsed = json.loads(content)
            print(f"\n✓ Successfully parsed as JSON:")
            print(json.dumps(parsed, indent=2))
            return True
        except Exception as e:
            print(f"\n✗ Failed to parse as JSON: {e}")
            return False
    else:
        print(f"✗ Request failed: {response.text}")
        return False


def test_judge_class():
    """Test 3: FireworksJudge class"""
    print("\n" + "="*70)
    print("TEST 3: FIREWORKSJUDGE CLASS")
    print("="*70)
    
    settings = get_settings()
    judge = FireworksJudge(settings)
    
    print(f"Judge available: {judge.available()}")
    
    system = "You are a JSON-only API. Respond ONLY with valid JSON."
    user = 'Return this exact JSON: {"fidelity": 0.8, "drift": 0.2, "preserved": ["test1", "test2"]}'
    
    try:
        response = judge.judge_text(
            system_prompt=system, 
            user_prompt=user, 
            temperature=0.0, 
            max_tokens=200
        )
        
        print(f"\nJudge Response:")
        print("-" * 70)
        print(response)
        print("-" * 70)
        
        if response:
            try:
                parsed = json.loads(response)
                print(f"\n✓ Successfully parsed as JSON:")
                print(json.dumps(parsed, indent=2))
                return True
            except Exception as e:
                print(f"\n✗ Failed to parse as JSON: {e}")
                print(f"First 200 chars: {response[:200]}")
                return False
        else:
            print("✗ Judge returned None")
            return False
            
    except Exception as e:
        print(f"✗ ERROR: {e}")
        return False


def test_evaluation_prompt():
    """Test 4: Actual evaluation prompt"""
    print("\n" + "="*70)
    print("TEST 4: ACTUAL EVALUATION PROMPT")
    print("="*70)
    
    settings = get_settings()
    judge = FireworksJudge(settings)
    
    system = (
        "You are a JSON-only API. Respond ONLY with valid JSON. "
        "No explanations, no reasoning, no markdown, no other text. "
        "Just the raw JSON object."
    )
    
    user = (
        "Evaluate how well RECEIVER preserved SENDER's information.\n\n"
        "SENDER:\n{\"user\": \"test\", \"preferences\": [\"action\", \"drama\"]}\n\n"
        "RECEIVER:\n{\"movies\": [{\"title\": \"Test\", \"genres\": [\"action\"]}]}\n\n"
        "Respond with ONLY this JSON (no other text):\n"
        '{"fidelity": <0.0-1.0>, "drift": <0.0-1.0>, "preserved": ["key1", "key2"]}\n\n'
        "JSON:"
    )
    
    try:
        response = judge.judge_text(
            system_prompt=system,
            user_prompt=user,
            temperature=0.0,
            max_tokens=384
        )
        
        print(f"\nEvaluation Response:")
        print("-" * 70)
        print(response)
        print("-" * 70)
        
        if response:
            try:
                parsed = json.loads(response)
                print(f"\n✓ Successfully parsed as JSON:")
                print(json.dumps(parsed, indent=2))
                
                # Check for required fields
                if "fidelity" in parsed and "drift" in parsed:
                    print(f"\n✓ Contains required fields")
                    return True
                else:
                    print(f"\n✗ Missing required fields")
                    return False
                    
            except Exception as e:
                print(f"\n✗ Failed to parse as JSON: {e}")
                print(f"Response type: {type(response)}")
                return False
        else:
            print("✗ Judge returned None")
            return False
            
    except Exception as e:
        print(f"✗ ERROR: {e}")
        return False


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("COMPREHENSIVE FIREWORKS API TEST SUITE")
    print("="*70)
    
    results = []
    
    results.append(("Basic Connection", test_basic_connection()))
    results.append(("JSON Instructions", test_json_instruction()))
    results.append(("Judge Class", test_judge_class()))
    results.append(("Evaluation Prompt", test_evaluation_prompt()))
    
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{test_name:<30} {status}")
    
    all_passed = all(result[1] for result in results)
    
    print("\n" + "="*70)
    if all_passed:
        print("✓ ALL TESTS PASSED")
    else:
        print("✗ SOME TESTS FAILED - See details above")
    print("="*70)


if __name__ == "__main__":
    main()
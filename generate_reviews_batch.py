import asyncio
import sys
import os

FILES = [
    ("2.11", "src/part1-fundamentals/ch02-rendering/11-flutter-rendering.md"),
    ("2.12", "src/part1-fundamentals/ch02-rendering/12-window-manager.md"),
    ("2.13", "src/part1-fundamentals/ch02-rendering/13-buffer-queue.md"),
    ("2.14", "src/part1-fundamentals/ch02-rendering/14-graphics-api-evolution.md"),
    ("2.15", "src/part1-fundamentals/ch02-rendering/15-dmabuf-gralloc.md"),
    ("2.16", "src/part1-fundamentals/ch02-rendering/16-sync-fence.md"),
    ("2.17", "src/part1-fundamentals/ch02-rendering/17-frame-pacing.md"),
    ("2.18", "src/part1-fundamentals/ch02-rendering/18-adaptive-refresh-rate.md"),
    ("2.19", "src/part1-fundamentals/ch02-rendering/19-refresh-rate-switching.md"),
    ("2.20", "src/part1-fundamentals/ch02-rendering/20-multiwindow-desktop-rendering.md"),
    ("2.21", "src/part1-fundamentals/ch02-rendering/21-text-rendering-performance.md"),
    ("2.README", "src/part1-fundamentals/ch02-rendering/README.md")
]

async def process_file(sem, file_id, file_path, pack_content):
    async with sem:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except FileNotFoundError:
            print(f"File not found: {file_path}")
            return
        
        prompt = f"""
You are the AIW external technical reviewer. 
Read the following AIW review specification:
{pack_content}

Now, perform a detailed technical review on the following file. 
Output ONLY the markdown report. DO NOT output any conversational text.
Follow the structure from the review pack (Section 8.5) precisely.

File content:
{content}
"""
        
        output_file = f"logs/external-review/2026-04-25-15-{file_id}-external-review.md"
        
        print(f"Starting review for {file_id}...")
        
        # Run gemini command and pass prompt via stdin
        process = await asyncio.create_subprocess_exec(
            "gemini", "-y", "-p", "Please read the prompt from stdin and generate the review.", "--raw-output",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate(input=prompt.encode('utf-8'))
        
        output_str = stdout.decode('utf-8')
        
        # Strip some verbose from gemini CLI if any
        if "Created execution plan" in output_str:
            output_str = output_str.split("Created execution plan")[0]
        
        os.makedirs("logs/external-review", exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(output_str.strip())
            
        print(f"Finished {file_id}. Saved to {output_file}")

async def main():
    try:
        with open("aiw-gemini-review-pack.md", 'r', encoding='utf-8') as f:
            pack_content = f.read()
    except FileNotFoundError:
        print("Review pack not found!")
        return

    sem = asyncio.Semaphore(4) # 4 concurrent requests
    
    tasks = []
    for file_id, file_path in FILES:
        tasks.append(process_file(sem, file_id, file_path, pack_content))
        
    await asyncio.gather(*tasks)
    print("All reviews generated.")

if __name__ == "__main__":
    asyncio.run(main())

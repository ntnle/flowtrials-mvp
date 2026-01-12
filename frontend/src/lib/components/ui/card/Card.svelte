<script>
  import { createEventDispatcher } from "svelte";
  import { cn } from "$lib/utils.js";

  let className = undefined;
  export { className as class };

  const dispatch = createEventDispatcher();

  function handleClick(event) {
    dispatch("click", event);
  }
</script>

<div
  class={cn(
    "rounded-lg border bg-card text-card-foreground shadow-sm",
    className
  )}
  on:click={handleClick}
  {...$$restProps}
>
  <slot />
</div>

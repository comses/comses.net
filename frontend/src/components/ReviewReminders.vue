<template>
  <div class="alert alert-danger mb-4" role="alert">
    <p>
      <i class="fas fa-exclamation-triangle"></i> Peer reviews must be requested on
      <strong>unpublished model releases</strong> so that you can continue to revise your submission
      based on reviewer guidance. If you have already published your model
      <strong>a new draft release will be created</strong> as an exact copy of your most recent
      published release.
    </p>
    <p class="mb-0">
      Once a model release passes peer review it will remain private until you choose to publish it,
      at which point you may set a version number. Please note that
      <strong>uploaded files cannot be modified after review</strong>
      regardless of published status, though metadata will remain editable.
    </p>
  </div>
  <p>
    Before submitting your peer review request, please ensure that your model conforms to the
    following <a href="/reviews/" target="_blank">review criteria</a>:
  </p>
  <div class="d-flex">
    <i class="fas fa-code pt-1" style="width: 1rem"></i>
    <div class="ps-3 flex-grow-1"><strong>Has "clean" source code</strong></div>
  </div>
  <small>
    <ul class="ps-5">
      <li>Uses meaningful variable, method, and/or class names</li>
      <li>Well structured and consistently formatted for readability</li>
      <li>Thorough comments that describe the semantics and intent of the code</li>
      <li>"As simple as possible but no simpler"</li>
    </ul>
  </small>
  <div class="d-flex">
    <i class="far fa-file-alt pt-1" style="width: 1rem"></i>
    <div class="ps-3 flex-grow-1"><strong>Has detailed narrative documentation</strong></div>
  </div>
  <small>
    <ul class="ps-5">
      <li>
        Contains equations, flowcharts, or other diagrams in a structured format like the
        <a href="https://www.ufz.de/index.php?de=40429" target="_blank">ODD protocol</a> or
        equivalent
      </li>
      <li>
        We <strong>do not recommend submitting a published journal article</strong> as narrative
        documentation as they are often not detailed enough to allow others to fully reproduce your
        model and pose copyright issues for us to host
      </li>
    </ul>
  </small>
  <div class="d-flex">
    <i class="fas fa-terminal pt-1" style="width: 1rem"></i>
    <div class="ps-3 flex-grow-1"><strong>Is easily runnable</strong></div>
  </div>
  <small>
    <ul class="ps-5">
      <li>Does not require substantive changes to the downloaded package to run</li>
      <li>
        The source code does not contain any absolute paths (e.g.
        <code>"/Users/twubc/Desktop/ferns.nc"</code>) and correctly references any uploaded data
        files (see note below)
      </li>
    </ul>
  </small>
  <div class="alert bg-gray" role="alert">
    <p><strong>Note on Uploaded Data</strong></p>
    <p class="mb-0">
      <small>
        CoMSES Net stores uploaded data files in <code>&lt;project-root&gt;/data/</code> and code in
        <code>&lt;project-root&gt;/code/</code>. This means that your model will need to reference
        uploaded data files via a relative path like <code>"../data/my-input-data.csv"</code>. If
        you uploaded a zipfile with a nested directory structure you may need to go up several
        directories to get to the project root before descending back down into the data directory,
        depending on where your source code files exist within that nested directory structure. For
        example, a Python script in a <code>src/python/</code> directory would have to reference
        uploaded data files in <code>"../../../data/"</code>). This limitation can be sidestepped by
        including your data in your source code zipfile and referencing relative paths to your input
        data directly in your code and ignoring the CoMSES data upload slot.
      </small>
    </p>
  </div>
</template>

<script setup lang="ts"></script>
